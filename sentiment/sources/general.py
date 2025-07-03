# general.py
import requests

NEWS_API_KEY = "d7d36a91040241a891c99d6a44e2a006"

class General:
    def get_data(self, ticker: str):
        try:
            response = requests.get(
                f"https://newsapi.org/v2/everything?q={ticker}&apiKey={NEWS_API_KEY}",
                timeout=5
            )
            response.raise_for_status()
            data = response.json()
            return [
                {
                    "title": article["title"],
                    "url": article["url"],
                    "source": article["source"]["name"]
                }
                for article in data.get("articles", [])[:5]
            ]
        except Exception as e:
            return [{"error": f"Could not fetch articles: {str(e)}"}]
