from fastapi import FastAPI, HTTPException
from sentiment.sources.general import General
from sentiment.sources.twitter import Twitter
from sentiment.sources.reddit import Reddit

app = FastAPI()

# Instantiate classes once
general = General()
twitter = Twitter()
reddit = Reddit()

@app.get("/")
def root():
    return {"message": "Sentiment API is running"}

@app.get("/sentiment/{source}/{ticker}")
def sentiment(source: str, ticker: str):
    source = source.lower()
    if source == "news":
        results = general.get_data(ticker)
    elif source == "twitter":
        results = twitter.get_data(ticker)
    elif source == "reddit":
        results = reddit.get_data(ticker)
    else:
        raise HTTPException(status_code=400, detail="Invalid source.")

    return {
        "source": source,
        "ticker": ticker.upper(),
        "results": results,
    }
