# main.py
from backend.ml_models.ProsusAI_finbert import finbert_classifier, finbert_probs, round_probs
from backend.ml_models.vader import classify_vader
from backend.app_reddit import fetch_reddit, router as reddit_router


from typing import List, Literal
from newspaper import Article as NewsArticle
from fastapi.responses import JSONResponse


from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yfinance as yf
from yfinance import Search

class Article(BaseModel):
    title: str
    link: str
    source: str

class NewsResponse(BaseModel):
    ticker: str
    articles: List[Article]

class SentimentRequest(BaseModel):
    classifier: str  # "finbert" or "vader"


class TextIn(BaseModel):
    text: str
    
CLASSIFIERS = {
    "finbertone": finbert_classifier,
    "finbertprobs": finbert_probs,
    "vader":   classify_vader,
}

app = FastAPI(
    title="Stock News Scraper",
    description="Returns the 5 most recent news articles for a given stock ticker.",
)
app.include_router(reddit_router)

def extract_article_content(url: str) -> str:
    try:
        article = NewsArticle(url)
        article.download()
        article.parse()
        return article.text
    except Exception as e:
        return f"Error fetching content: {e}"

# This only gives the top 5 article titles and links, not full text
@app.get("/api/scrapenews/{ticker}", response_model=NewsResponse)
def scrape_news(ticker: str):
    ticker = ticker.upper()

    # 1. Try to fetch the top 5 news items via the Search API
    try:
        search = Search(ticker, news_count=5)
        news_items = search.news
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching news: {e}")

    # 2. If we got nothing back, 404
    if not news_items:
        raise HTTPException(status_code=404, detail=f"No news found for ticker '{ticker}'")

    # 3. Pick out the right fields (there are a few possible key names)
    articles = []
    for item in news_items:
        title  = item.get("title") or item.get("headline") or "No title"
        link   = item.get("link")  or item.get("url")      or ""
        source = (
            item.get("publisher")
            or item.get("source")
            or item.get("provider")
            or "Unknown source"
        )
        articles.append(Article(title=title, link=link, source=source))

    return NewsResponse(ticker=ticker, articles=articles)

# This gives the full text of each article
@app.get("/api/fullarticles/{ticker}")
def get_full_articles(ticker: str):
    # Step 1: Get article metadata using your existing function
    news_response = scrape_news(ticker)

    # Step 2: Extract full text from each article link
    contents = []
    for article in news_response.articles:
        content = extract_article_content(article.link)
        contents.append({
            "title": article.title,
            "source": article.source,
            "link": article.link,
            "content": content
        })

    return {
        "ticker": ticker,
        "full_articles": contents
    }

# This gives all the 5 texts in an array, without titles or sources
@app.get("/api/articletexts/{ticker}")
def get_article_texts(ticker: str):
    news_response = scrape_news(ticker)

    contents = []
    for article in news_response.articles:
        content = extract_article_content(article.link)
        contents.append(content)

    return {
        "ticker": ticker,
        "article_texts": contents
    }

# ------

@app.post("/api/_debug/vader")
def debug_vader(body: TextIn):
    return classify_vader(body.text)

@app.post("/api/_debug/finbert")
def debug_finbert(body: TextIn):
    return finbert_classifier(body.text)

@app.post("/api/_debug/finbert_probs")
def debug_finbert_probs(body: TextIn):
    return round_probs(finbert_probs(body.text))

def to_label(pred):
    if isinstance(pred, list) and pred and isinstance(pred[0], dict) and "label" in pred[0]:
        return pred[0]["label"]
    if isinstance(pred, dict) and "label" in pred:
        return pred["label"]
    return str(pred)

def fetch_article_texts_array(ticker: str) -> list[str]:
    """
    Returns just the article texts as a Python list.
    Works whether get_article_texts returns a dict or a JSONResponse.
    """
    resp = get_article_texts(ticker)

    if isinstance(resp, JSONResponse):
        try:
            data = json.loads(resp.body.decode("utf-8"))
        except Exception as e:
            raise HTTPException(500, f"Could not parse JSONResponse: {e}")
    elif isinstance(resp, dict):
        data = resp
    else:
        raise HTTPException(500, f"Unexpected return type from get_article_texts: {type(resp)}")

    texts = data.get("article_texts")
    if not isinstance(texts, list):
        raise HTTPException(500, "get_article_texts returned no 'article_texts' list")
    return texts

@app.post("/api/sentiment/{ticker}")
def analyze_article_sentiment(ticker: str, req: SentimentRequest):
    texts = fetch_article_texts_array(ticker)
    key = req.classifier.lower()
    if key not in CLASSIFIERS:
        raise HTTPException(400, f"Unknown classifier '{req.classifier}'. Use one of: {list(CLASSIFIERS.keys())}")
    clf = CLASSIFIERS[key]
    
    try:
        if key == "finbertprobs":
            # return all three probabilities per article
            predictions = [round_probs(clf(t)) for t in texts]
        else:
            # return a single top label per article
            raw = [clf(t) for t in texts]  # each is {'label','score'} or similar
            def to_label(pred):
                if isinstance(pred, dict) and "label" in pred:
                    return pred["label"]
                if isinstance(pred, list) and pred and isinstance(pred[0], dict) and "label" in pred[0]:
                    return pred[0]["label"]
                return str(pred)
            predictions = [to_label(p) for p in raw]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"classifier failed: {e}")

    return {
        "ticker": ticker,
        "classifier": key,
        "count": len(texts),
        "predictions": predictions
    }
    
