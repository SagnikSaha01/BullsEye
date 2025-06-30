# main.py
from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yfinance as yf

class Article(BaseModel):
    title: str
    link: str
    source: str

class NewsResponse(BaseModel):
    ticker: str
    articles: List[Article]

app = FastAPI(
    title="Stock News Scraper",
    description="Returns the 5 most recent news articles for a given stock ticker.",
)

@app.get("/api/scrapenews/{ticker}", response_model=NewsResponse)
def scrape_news(ticker: str):
    # 1. Fetch news items from Yahoo Finance via yfinance
    try:
        ticker_obj = yf.Ticker(ticker)
        news_items = ticker_obj.news
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching news: {e}")

    # 2. If no news, return 404
    if not news_items:
        raise HTTPException(status_code=404, detail=f"No news found for ticker '{ticker}'")

    # 3. Build our response, slicing to the first 5 items
    articles = []
    for item in news_items[:5]:
        articles.append(Article(
            title=item.get("title", "No title"),
            link=item.get("link", ""),
            source=item.get("publisher", "Unknown source")
        ))

    return NewsResponse(ticker=ticker.upper(), articles=articles)
