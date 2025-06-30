# main.py
from typing import List

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

app = FastAPI(
    title="Stock News Scraper",
    description="Returns the 5 most recent news articles for a given stock ticker.",
)

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
