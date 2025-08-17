# app_reddit.py
import os
import re
import html
from typing import List, Optional, Set, Dict
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi import APIRouter
from backend.ml_models.vader import classify_vader
from backend.ml_models.ProsusAI_finbert import finbert_classifier, finbert_probs, round_probs
from backend.newsAPI import calculate_average_sentiment
import praw

load_dotenv()

router = APIRouter()

CLASSIFIERS = {
    "vader": classify_vader,
    "finbert": finbert_classifier,
    "finbertprobs": finbert_probs,
}

class SentimentRequest(BaseModel):
    classifier: str
    timeframe: Optional[str] = "day"
    limit_posts: Optional[int] = 80
    include_comments: Optional[bool] = True
    comments_per_post: Optional[int] = 8
    include_finance_subs: Optional[bool] = True


# ---------- Reddit OAuth via PRAW ----------
def get_reddit_client() -> praw.Reddit:
    try:
        reddit = praw.Reddit(
            client_id=os.environ["REDDIT_CLIENT_ID"],
            client_secret=os.environ["REDDIT_CLIENT_SECRET"],
            # username=os.environ["REDDIT_USERNAME"],
            # password=os.environ["REDDIT_PASSWORD"],
            user_agent=os.environ.get("REDDIT_USER_AGENT", "stock-sentiment/0.1"),
        )
        # Lightweight sanity call (won't hit rate limits badly)
        _ = reddit.read_only  # True for script creds when just reading
        return reddit
    except KeyError as e:
        raise RuntimeError(f"Missing env var: {e}")

# ---------- Simple ticker -> company helper (extend as you like) ----------
TICKER_TO_COMPANY: Dict[str, str] = {
    "AAPL": "Apple",
    "TSLA": "Tesla",
    "NVDA": "NVIDIA",
    "MSFT": "Microsoft",
    "AMZN": "Amazon",
    "GOOGL": "Google",
    "META": "Meta",
}

# ---------- Cleaning utilities ----------
URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
INLINE_CODE_RE = re.compile(r"`{1,3}.*?`{1,3}", re.DOTALL)
CODE_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)
MARKDOWN_ARTIFACTS_RE = re.compile(r"[*_>#-]{1,3}|\|")
EMOJI_RE = re.compile(
    "["                     # very broad emoji/pictograph ranges
    "\U0001F600-\U0001F64F" # emoticons
    "\U0001F300-\U0001F5FF" # symbols & pictographs
    "\U0001F680-\U0001F6FF" # transport & map
    "\U0001F1E0-\U0001F1FF" # flags
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "]+",
    flags=re.UNICODE
)

def clean_text(s: str, max_len: int = 2000) -> str:
    if not s:
        return ""
    s = html.unescape(s)

    # Remove code blocks & inline code early
    s = CODE_BLOCK_RE.sub(" ", s)
    s = INLINE_CODE_RE.sub(" ", s)

    # Convert [text](url) to "text"
    s = MARKDOWN_LINK_RE.sub(lambda m: m.group(1), s)

    # Strip URLs
    s = URL_RE.sub(" ", s)

    # Remove markdown artifacts (#, *, _, >, |) used for formatting
    s = MARKDOWN_ARTIFACTS_RE.sub(" ", s)

    # Remove emojis
    s = EMOJI_RE.sub(" ", s)

    # Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()

    # Bound length to make downstream ML fast
    if len(s) > max_len:
        s = s[:max_len] + "…"
    return s

# ---------- Fetch logic ----------
DEFAULT_FINANCE_SUBS = [
    "stocks", "investing", "wallstreetbets",
    "securityanalysis", "StockMarket", "options"
]

class RedditResponse(BaseModel):
    platform: str = "reddit"
    query: str
    timeframe: str
    counts: dict
    texts: List[str]

# app = FastAPI(title="Reddit Adapter for Stock Sentiment")

@router.get("/reddit/fetch", response_model=RedditResponse)
def fetch_reddit(
    ticker: str = Query(..., min_length=1, description="e.g., TSLA"),
    company: Optional[str] = Query(None, description='e.g., "Tesla" (auto-mapped if omitted)'),
    timeframe: str = Query("day", pattern="^(hour|day|week|month|year|all)$"),
    limit_posts: int = Query(80, ge=10, le=300, description="Total posts across sources"),
    include_comments: bool = Query(True),
    comments_per_post: int = Query(8, ge=0, le=30),
    include_finance_subs: bool = Query(True),
):
    """
    Returns a list of cleaned Reddit texts (titles, selftext, and top N comments) for the given ticker/company.
    No sentiment is applied here—this endpoint is for text collection + cleaning.
    """
    rd = get_reddit_client()

    tk = ticker.upper().strip()
    co = (company or TICKER_TO_COMPANY.get(tk) or tk).strip()

    # Build a simple Boolean query for Reddit search
    query = f'("{tk}" OR "{co}")'

    texts: List[str] = []
    seen: Set[str] = set()

    # Split post budget between sitewide and finance subs if enabled
    budget_all = limit_posts // 2 if include_finance_subs else limit_posts
    budget_subs = limit_posts - budget_all

    # -------- A) Sitewide search (r/all) --------
    try:
        submissions_all = rd.subreddit("all").search(
            query=query,
            sort="new",               # return newest first
            time_filter=timeframe,    # "day"/"week"/...
            limit=budget_all or None  # None lets PRAW page up to ~1000 if needed
        )
        for s in submissions_all:
            # Titles + selftext
            for piece in (s.title or "", getattr(s, "selftext", "") or ""):
                c = clean_text(piece)
                if c and c not in seen:
                    texts.append(c)
                    seen.add(c)

            # Small slice of top comments
            if include_comments and comments_per_post > 0:
                try:
                    s.comment_sort = "top"
                    s.comments.replace_more(limit=0)  # don't expand deep trees
                    for c in list(s.comments)[:comments_per_post]:
                        body = clean_text(getattr(c, "body", "") or "", max_len=1000)
                        if body and body not in seen:
                            texts.append(body)
                            seen.add(body)
                except Exception:
                    # Ignore comment-level fetch issues to keep the endpoint resilient
                    pass

    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Reddit sitewide search failed: {e}")

    # -------- B) Targeted finance subreddits --------
    if include_finance_subs and budget_subs > 0:
        per_sub = max(10, budget_subs // max(1, len(DEFAULT_FINANCE_SUBS)))
        for sub in DEFAULT_FINANCE_SUBS:
            try:
                submissions_sub = rd.subreddit(sub).search(
                    query=query,
                    sort="new",
                    time_filter=timeframe,
                    limit=per_sub
                )
                for s in submissions_sub:
                    for piece in (s.title or "", getattr(s, "selftext", "") or ""):
                        c = clean_text(piece)
                        if c and c not in seen:
                            texts.append(c)
                            seen.add(c)

                    if include_comments and comments_per_post > 0:
                        try:
                            s.comment_sort = "top"
                            s.comments.replace_more(limit=0)
                            for c in list(s.comments)[:comments_per_post]:
                                body = clean_text(getattr(c, "body", "") or "", max_len=1000)
                                if body and body not in seen:
                                    texts.append(body)
                                    seen.add(body)
                        except Exception:
                            pass
            except Exception:
                # Ignore a single sub failure; keep going
                continue

    return RedditResponse(
        query=query,
        timeframe=timeframe,
        counts={"unique_texts": len(texts)},
        texts=texts,
    )

# If you want to run directly:
# uvicorn app_reddit:app --reload --port 8000

@router.post("/api/sentiment/reddit/{ticker}")
def analyze_reddit_sentiment(ticker: str, req: SentimentRequest):
    """
    Fetch Reddit posts for a ticker and perform sentiment analysis on the texts.
    """
    # Get texts using existing fetch_reddit logic
    reddit_response = fetch_reddit(
        ticker=ticker,
        company=None,
        timeframe=req.timeframe,
        limit_posts=req.limit_posts,
        include_comments=req.include_comments,
        comments_per_post=req.comments_per_post,
        include_finance_subs=req.include_finance_subs,
    )
    
    texts = reddit_response.texts
    
    # Validate classifier
    key = req.classifier.lower()
    if key not in CLASSIFIERS:
        raise HTTPException(400, f"Unknown classifier '{req.classifier}'. Use one of: {list(CLASSIFIERS.keys())}")
    
    clf = CLASSIFIERS[key]
    
    # Perform sentiment analysis
    try:
        if key == "finbertprobs":
            # return all three probabilities per text
            predictions = [round_probs(clf(t)) for t in texts]
        else:
            # return a single top label per text
            raw = [clf(t) for t in texts]
            
            def to_label(pred):
                if isinstance(pred, dict) and "label" in pred:
                    return pred["label"]
                if isinstance(pred, list) and pred and isinstance(pred[0], dict) and "label" in pred[0]:
                    return pred[0]["label"]
                return str(pred)
            
            predictions = [to_label(p) for p in raw]
        
        average_sentiment = calculate_average_sentiment(predictions, key)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Classifier failed: {e}")

    return {
        "ticker": ticker,
        "classifier": key,
        "platform": "reddit",
        "query": reddit_response.query,
        "timeframe": req.timeframe,
        "count": len(texts),
        "predictions": predictions,
        "average_sentiment": average_sentiment,
    }