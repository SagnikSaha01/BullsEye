# app_news.py
import os
import re
import html
from typing import List, Optional, Set, Dict
from fastapi import FastAPI, HTTPException, Query, APIRouter
from pydantic import BaseModel
from dotenv import load_dotenv
import requests

# Import your ML models (adjust paths as needed)
from backend.ml_models.vader import classify_vader
from backend.ml_models.ProsusAI_finbert import finbert_classifier, finbert_probs, round_probs

load_dotenv()

router = APIRouter()

# Your API key (consider moving to environment variables)
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "d7d36a91040241a891c99d6a44e2a006")

CLASSIFIERS = {
    "vader": classify_vader,
    "finbert": finbert_classifier,
    "finbertprobs": finbert_probs,
}

class SentimentRequest(BaseModel):
    classifier: str
    limit_articles: Optional[int] = 50
    include_description: Optional[bool] = True
    sort_by: Optional[str] = "publishedAt"  # publishedAt, relevancy, popularity

class NewsResponse(BaseModel):
    platform: str = "news"
    query: str
    counts: dict
    texts: List[str]
    articles: List[dict]

# ---------- Text cleaning utilities ----------
URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
INLINE_CODE_RE = re.compile(r"`{1,3}.*?`{1,3}", re.DOTALL)
CODE_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)
MARKDOWN_ARTIFACTS_RE = re.compile(r"[*_>#-]{1,3}|\|")
EMOJI_RE = re.compile(
    "["                     
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
    """Clean and normalize text for sentiment analysis"""
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
    
    # Remove markdown artifacts
    s = MARKDOWN_ARTIFACTS_RE.sub(" ", s)
    
    # Remove emojis
    s = EMOJI_RE.sub(" ", s)
    
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    
    # Bound length
    if len(s) > max_len:
        s = s[:max_len] + "…"
    return s

# ---------- News fetching logic ----------
class General:
    def __init__(self):
        self.api_key = NEWS_API_KEY
    
    def get_data(self, ticker: str, limit: int = 50, sort_by: str = "publishedAt"):
        """
        Fetch news articles for a given ticker
        """
        try:
            # Build search query - you can enhance this
            query = f'"{ticker}" OR "{ticker} stock" OR "{ticker} company"'
            
            params = {
                "q": query,
                "apiKey": self.api_key,
                "language": "en",
                "sortBy": sort_by,
                "pageSize": min(limit, 100)  # NewsAPI max is 100
            }
            
            response = requests.get(
                "https://newsapi.org/v2/everything",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            articles = []
            for article in data.get("articles", []):
                # Skip articles with missing essential data
                if not article.get("title") or article.get("title") == "[Removed]":
                    continue
                    
                articles.append({
                    "title": article["title"],
                    "description": article.get("description", ""),
                    "url": article["url"],
                    "source": article["source"]["name"],
                    "publishedAt": article.get("publishedAt"),
                    "author": article.get("author")
                })
            
            return articles
            
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=502, detail=f"News API request failed: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Could not fetch articles: {str(e)}")

@router.get("/news/fetch", response_model=NewsResponse)
def fetch_news(
    ticker: str = Query(..., min_length=1, description="e.g., AAPL"),
    limit_articles: int = Query(50, ge=10, le=100, description="Number of articles to fetch"),
    sort_by: str = Query("publishedAt", regex="^(publishedAt|relevancy|popularity)$"),
    include_description: bool = Query(True, description="Include article descriptions in analysis")
):
    """
    Fetch news articles for a given ticker.
    Returns cleaned texts for sentiment analysis.
    """
    general = General()
    articles = general.get_data(ticker, limit=limit_articles, sort_by=sort_by)
    
    if not articles:
        raise HTTPException(status_code=404, detail="No articles found for the given ticker")
    
    texts: List[str] = []
    seen: Set[str] = set()
    
    for article in articles:
        # Always include title
        title = clean_text(article.get("title", ""))
        if title and title not in seen:
            texts.append(title)
            seen.add(title)
        
        # Optionally include description
        if include_description:
            description = clean_text(article.get("description", ""))
            if description and description not in seen and len(description) > 20:
                texts.append(description)
                seen.add(description)
    
    return NewsResponse(
        query=f'"{ticker}" news',
        counts={"articles": len(articles), "unique_texts": len(texts)},
        texts=texts,
        articles=articles
    )

def calculate_average_sentiment(predictions, classifier_key):
    """Calculate average sentiment based on classifier type"""
    valid_predictions = [p for p in predictions if p != "error" and not (isinstance(p, dict) and p.get("error"))]
    
    if not valid_predictions:
        return {"error": "No valid predictions to average"}
    
    if classifier_key == "finbertprobs":
        # Average the probabilities
        total_negative = sum(p.get("negative", 0) for p in valid_predictions)
        total_neutral = sum(p.get("neutral", 0) for p in valid_predictions)
        total_positive = sum(p.get("positive", 0) for p in valid_predictions)
        count = len(valid_predictions)
        
        return {
            "negative": round(total_negative / count, 3),
            "neutral": round(total_neutral / count, 3),
            "positive": round(total_positive / count, 3)
        }
    else:
        # Count occurrences and return most common
        from collections import Counter
        label_counts = Counter(valid_predictions)
        most_common = label_counts.most_common(1)[0] if label_counts else ("neutral", 0)
        
        return {
            "dominant_sentiment": most_common[0],
            "confidence": f"{most_common[1]}/{len(valid_predictions)}",
            "breakdown": dict(label_counts)
        }

@router.post("/api/sentiment/news/{ticker}")
def analyze_news_sentiment(ticker: str, req: SentimentRequest):
    """
    Fetch news articles for a ticker and perform sentiment analysis on the texts.
    """
    # Get texts using existing fetch_news logic
    news_response = fetch_news(
        ticker=ticker,
        limit_articles=req.limit_articles,
        sort_by=req.sort_by,
        include_description=req.include_description,
    )
    
    texts = news_response.texts
    articles = news_response.articles
    
    # Create mapping from text to article info
    text_to_article = {}
    seen_texts = set()
    
    for article in articles:
        title = clean_text(article.get("title", ""))
        if title and title not in seen_texts:
            text_to_article[title] = {
                "title": article.get("title"),
                "url": article.get("url"),
                "source": article.get("source"),
                "publishedAt": article.get("publishedAt"),
                "type": "title"
            }
            seen_texts.add(title)
        
        if req.include_description:
            description = clean_text(article.get("description", ""))
            if description and description not in seen_texts and len(description) > 20:
                text_to_article[description] = {
                    "title": article.get("title"),
                    "url": article.get("url"),
                    "source": article.get("source"),
                    "publishedAt": article.get("publishedAt"),
                    "type": "description"
                }
                seen_texts.add(description)
    
    # Validate classifier
    key = req.classifier.lower()
    if key not in CLASSIFIERS:
        raise HTTPException(400, f"Unknown classifier '{req.classifier}'. Use one of: {list(CLASSIFIERS.keys())}")
    
    clf = CLASSIFIERS[key]
    
    # Perform sentiment analysis and create detailed results
    try:
        detailed_predictions = []
        
        for text in texts:
            article_info = text_to_article.get(text, {})
            
            if key == "finbertprobs":
                prediction = round_probs(clf(text))
            else:
                raw_pred = clf(text)
                
                def to_label(pred):
                    if isinstance(pred, dict) and "label" in pred:
                        return pred["label"]
                    if isinstance(pred, list) and pred and isinstance(pred[0], dict) and "label" in pred[0]:
                        return pred[0]["label"]
                    return str(pred)
                
                prediction = to_label(raw_pred)
            
            detailed_predictions.append({
                "text": text[:100] + "..." if len(text) > 100 else text,  # Truncate for readability
                "prediction": prediction,
                "article_title": article_info.get("title"),
                "article_url": article_info.get("url"),
                "source": article_info.get("source"),
                "publishedAt": article_info.get("publishedAt"),
                "text_type": article_info.get("type")  # "title" or "description"
            })
        
        # Also provide simple predictions array for backward compatibility
        simple_predictions = [item["prediction"] for item in detailed_predictions]
        
        # Calculate average sentiment
        average_sentiment = calculate_average_sentiment(simple_predictions, key)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Classifier failed: {e}")

    return {
        "ticker": ticker,
        "classifier": key,
        "platform": "news",
        "query": news_response.query,
        "sort_by": req.sort_by,
        "count": len(texts),
        "articles_count": news_response.counts["articles"],
        "predictions": simple_predictions,  # Simple array for backward compatibility
        "detailed_predictions": detailed_predictions,  # Detailed info with URLs
        "average_sentiment": average_sentiment,  # New average sentiment
        "summary": {
            "total_articles": len(articles),
            "total_texts_analyzed": len(texts),
            "unique_sources": len(set(a.get("source", "") for a in articles if a.get("source")))
        }
    }

# Test function (for development)
if __name__ == "__main__":
    # Test the General class
    general = General()
    ticker = "AAPL"
    print(f"Testing get_data function with ticker: {ticker}")
    result = general.get_data(ticker)
    print("Result:")
    for i, article in enumerate(result[:3]):
        print(f"{i+1}. {article['title']}")
        print(f"   Source: {article['source']}")
        print(f"   URL: {article['url'][:50]}...")
        print()