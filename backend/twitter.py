# twitter.py
import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Path
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline

load_dotenv()

BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
router = APIRouter()

# Load finbert
model_name = "yiyanghkust/finbert-tone"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model     = AutoModelForSequenceClassification.from_pretrained(model_name)
sentiment_pipeline = pipeline("sentiment-analysis", model=model, tokenizer=tokenizer)


@router.get(
    "/{day}/twitter/{ticker}",
    summary="Fetch tweets mentioning a ticker on a given day",
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

    #build twitter query
    query = (
        f'("{ticker}" OR "${ticker}" OR "stock {ticker}" '
        f'OR "shares {ticker}" OR "#{ticker}") lang:en -is:retweet'
    )

    params = {
        "query": query,
        "start_time": start_time,
        "end_time": end_time,
        "max_results": 10,
        "tweet.fields": "id,text,author_id,created_at",
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
    # runs finbert on each tweet and adds a "sentiment" key with label and score values to each json in the dictionary
    for tweet in data.get("data", []):
        out = sentiment_pipeline(tweet["text"])[0]
        tweet["sentiment"] = {"label": out["label"], "score": out["score"]}

    return {
        "ticker": ticker.upper(),
        "date": day,
        "twitter_response": data,
    }
