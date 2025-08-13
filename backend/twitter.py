# twitter.py
import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Path
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline

load_dotenv()

BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
if not BEARER_TOKEN:
    raise RuntimeError("TWITTER_BEARER_TOKEN is not set in the environment")

router = APIRouter()

# Load finbert
model_name = "yiyanghkust/finbert-tone"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model     = AutoModelForSequenceClassification.from_pretrained(model_name)
sentiment_pipeline = pipeline("sentiment-analysis", model=model, tokenizer=tokenizer)


@router.get(
    "/{day}/twitter/{ticker}",
    summary="Fetch tweets mentioning a ticker on a given day (authors >1M followers)",
    response_model=dict,
)
def scrape_twitter(
    day: str = Path(..., description="Date in YYYY-MM-DD format"),
    ticker: str = Path(..., description="Stock ticker, e.g. AAPL"),
):
    # parse date
    try:
        dt = datetime.strptime(day, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="`day` must be YYYY-MM-DD")
    start_time = dt.isoformat() + "Z"
    end_time   = (dt + timedelta(days=1)).isoformat() + "Z"

    # build twitter query (note: follower filters are not supported in query DSL)
    query = (
        f'("{ticker}" OR "${ticker}" OR "stock {ticker}" '
        f'OR "shares {ticker}" OR "#{ticker}") lang:en -is:retweet'
    )

    params = {
        "query": query,
        "start_time": start_time,
        "end_time": end_time,
        "max_results": 100,  # fetch as many as allowed per page, then filter
        "tweet.fields": "id,text,author_id,created_at,public_metrics",
        "expansions": "author_id",
        "user.fields": "id,name,username,verified,public_metrics",
    }
    headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}

    resp = requests.get(
        "https://api.twitter.com/2/tweets/search/recent",
        headers=headers,
        params=params,
    )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"Twitter API error: {resp.text}"
        )

    data = resp.json()
    tweets = data.get("data", [])
    users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}

    # keep only tweets whose authors have > 1,000,000 followers
    million_plus = []
    for tw in tweets:
        author = users.get(tw["author_id"])
        if not author:
            continue
        followers = author.get("public_metrics", {}).get("followers_count", 0)
        if followers >= 1_000_000:
            # attach author info for convenience
            tw["author"] = {
                "id": author["id"],
                "name": author.get("name"),
                "username": author.get("username"),
                "verified": author.get("verified"),
                "followers_count": followers,
            }
            million_plus.append(tw)

    # run FinBERT on filtered tweets
    for tweet in million_plus:
        out = sentiment_pipeline(tweet["text"])[0]
        tweet["sentiment"] = {"label": out["label"], "score": float(out["score"])}

    return {
        "ticker": ticker.upper(),
        "date": day,
        "count_total": len(tweets),
        "count_million_plus": len(million_plus),
        "tweets": million_plus,
        "note": "Filtered to authors with >1,000,000 followers using users.public_metrics.followers_count.",
    }