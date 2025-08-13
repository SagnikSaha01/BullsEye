from fastapi import FastAPI

api = FastAPI(title="Stock News Scraper")

@api.get("/")
def index():
    return {"message": "Hello World"}

# Import your router only after app is created
try:
    from twitter import router as twitter_router
    api.include_router(twitter_router, prefix="/scrapedata")
except RuntimeError as e:
    # If token/model missing, log the error but keep server alive
    print(f"[WARN] Twitter router not loaded: {e}")
