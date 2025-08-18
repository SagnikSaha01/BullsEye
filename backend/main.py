# main.py
from typing import List, Literal
import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from newspaper import Article as NewsArticle
import yfinance as yf
from yfinance import Search

from backend.ml_models.ProsusAI_finbert import finbert_classifier, finbert_probs, round_probs
from backend.ml_models.vader import classify_vader
from backend.app_reddit import fetch_reddit, router as reddit_router
from backend.newsAPI import calculate_average_sentiment, router as news_router


class Article(BaseModel):
    title: str
    link: str
    source: str

class NewsResponse(BaseModel):
    ticker: str
    articles: List[Article]

class SentimentRequest(BaseModel):
    classifier: str  # "finbertone", "finbertprobs", or "vader"

class TextIn(BaseModel):
    text: str


CLASSIFIERS = {
    "finbertone": finbert_classifier,
    "finbertprobs": finbert_probs,
    "vader": classify_vader,
}

app = FastAPI(
    title="Stock News Scraper",
    description="Returns the 5 most recent news articles for a given stock ticker.",
)

# CORS so the browser can call your API from a file:// page or another port
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # For dev; restrict in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Your extra routers
app.include_router(reddit_router)
app.include_router(news_router)


def extract_article_content(url: str) -> str:
    try:
        article = NewsArticle(url)
        article.download()
        article.parse()
        return article.text
    except Exception as e:
        return f"Error fetching content: {e}"


# ---------- Yahoo Finance News (metadata only) ----------
@app.get("/api/yf/scrapenews/{ticker}", response_model=NewsResponse, include_in_schema=False)
def scrape_news(ticker: str):
    ticker = ticker.upper()
    try:
        search = Search(ticker, news_count=5)
        news_items = search.news
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching news: {e}")

    if not news_items:
        raise HTTPException(status_code=404, detail=f"No news found for ticker '{ticker}'")

    articles = []
    for item in news_items:
        title = item.get("title") or item.get("headline") or "No title"
        link = item.get("link") or item.get("url") or ""
        source = (
            item.get("publisher")
            or item.get("source")
            or item.get("provider")
            or "Unknown source"
        )
        articles.append(Article(title=title, link=link, source=source))

    return NewsResponse(ticker=ticker, articles=articles)


# ---------- Full article extraction (content) ----------
@app.get("/api/yf/fullarticles/{ticker}", include_in_schema=False)
def get_full_articles(ticker: str):
    news_response = scrape_news(ticker)
    contents = []
    for article in news_response.articles:
        content = extract_article_content(article.link)
        contents.append({
            "title": article.title,
            "source": article.source,
            "link": article.link,
            "content": content
        })
    return {"ticker": ticker, "full_articles": contents}


@app.get("/api/yf/articletexts/{ticker}", include_in_schema=False)
def get_article_texts(ticker: str):
    news_response = scrape_news(ticker)
    contents = []
    for article in news_response.articles:
        content = extract_article_content(article.link)
        contents.append(content)
    return {"ticker": ticker, "article_texts": contents}


# ---------- Debug endpoints ----------
@app.post("/api/_debug/vader", include_in_schema=False)
def debug_vader(body: TextIn):
    return classify_vader(body.text)

@app.post("/api/_debug/finbert", include_in_schema=False)
def debug_finbert(body: TextIn):
    return finbert_classifier(body.text)

@app.post("/api/_debug/finbert_probs", include_in_schema=False)
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


def fetch_full_articles_data(ticker: str) -> list[dict]:
    """
    Returns full article data including metadata and content.
    """
    resp = get_full_articles(ticker)

    if isinstance(resp, JSONResponse):
        try:
            data = json.loads(resp.body.decode("utf-8"))
        except Exception as e:
            raise HTTPException(500, f"Could not parse JSONResponse: {e}")
    elif isinstance(resp, dict):
        data = resp
    else:
        raise HTTPException(500, f"Unexpected return type from get_full_articles: {type(resp)}")

    articles = data.get("full_articles")
    if not isinstance(articles, list):
        raise HTTPException(500, "get_full_articles returned no 'full_articles' list")
    return articles


# ---------- Sentiment (Yahoo Finance-sourced articles) ----------
@app.post("/api/yf/sentiment/{ticker}", include_in_schema=False)
def analyze_article_sentiment(ticker: str, req: SentimentRequest):
    full_articles = fetch_full_articles_data(ticker)
    texts = [article.get("content", "") for article in full_articles]

    key = req.classifier.lower()
    if key not in CLASSIFIERS:
        raise HTTPException(400, f"Unknown classifier '{req.classifier}'. Use one of: {list(CLASSIFIERS.keys())}")
    clf = CLASSIFIERS[key]

    try:
        detailed_predictions = []

        for i, (text, article) in enumerate(zip(texts, full_articles)):
            if not text or text.startswith("Error fetching content:"):
                prediction = "error" if key != "finbertprobs" else {"negative": 0, "neutral": 0, "positive": 0, "error": True}
            else:
                if key == "finbertprobs":
                    prediction = round_probs(clf(text))
                else:
                    raw_pred = clf(text)
                    def to_label_local(pred):
                        if isinstance(pred, dict) and "label" in pred:
                            return pred["label"]
                        if isinstance(pred, list) and pred and isinstance(pred[0], dict) and "label" in pred[0]:
                            return pred[0]["label"]
                        return str(pred)
                    prediction = to_label_local(raw_pred)

            detailed_predictions.append({
                "article_index": i + 1,
                "title": article.get("title", ""),
                "source": article.get("source", ""),
                "url": article.get("link", ""),
                "prediction": prediction,
                "content_preview": text[:200] + "..." if len(text) > 200 else text,
                "content_available": bool(text and not text.startswith("Error fetching content:"))
            })

        simple_predictions = [item["prediction"] for item in detailed_predictions]
        average_sentiment = calculate_average_sentiment(simple_predictions, key)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"classifier failed: {e}")

    return {
        "ticker": ticker.upper(),
        "classifier": key,
        "platform": "yahoo_finance",
        "count": len(texts),
        "predictions": simple_predictions,
        "detailed_predictions": detailed_predictions,
        "average_sentiment": average_sentiment,
        "summary": {
            "total_articles": len(full_articles),
            "successful_extractions": sum(1 for item in detailed_predictions if item["content_available"]),
            "failed_extractions": sum(1 for item in detailed_predictions if not item["content_available"])
        }
    }


# Optional convenience: GET wrapper so you can call it from the browser:
@app.get("/api/yf/sentiment/{ticker}")
def analyze_article_sentiment_get(ticker: str, classifier: str = "vader"):
    return analyze_article_sentiment(ticker, SentimentRequest(classifier=classifier))
