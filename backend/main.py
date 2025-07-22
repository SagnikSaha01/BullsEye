from fastapi import FastAPI
from twitter import router as twitter_router

print("Hello World")

api = FastAPI(title="Stock News Scraper")

api.include_router(twitter_router, prefix="/scrapedata")

@api.get("/")
def index():
    return {"message": "Hello World"}
