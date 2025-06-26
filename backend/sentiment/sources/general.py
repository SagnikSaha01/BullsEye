from sentiment.analyzer import analyze_sentiment

def fetch_general_articles(ticker: str):
    # Replace with real news scraping logic
    articles = [
        f"{ticker} reports record earnings in Q2",
        f"{ticker} faces lawsuit over environmental issues"
    ]
    return [{"text": article, "sentiment": analyze_sentiment(article)} for article in articles]
