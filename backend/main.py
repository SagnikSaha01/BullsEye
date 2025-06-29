from fastapi import FastAPI
import requests
from bs4 import BeautifulSoup
api = FastAPI()

@api.get('/api/{stock_ticker}')
def index(stock_ticker) -> float:
    data = getStockData(stock_ticker)
    print(data)
    print(findLinks(stock_ticker))
    return data['c']


def getStockData(ticker):
    header = {'X-Finnhub-Token' : 'd1fgsu1r01qig3h1ompgd1fgsu1r01qig3h1omq0'}
    res = requests.get("https://finnhub.io/api/v1/quote?symbol=" + ticker, headers=header)
    return res.json()

def findLinks(ticker):
    # search_url = "https://news.google.com/search?q=News about " + ticker
    url = f"https://finance.yahoo.com/quote/{ticker}?p={ticker}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Error: Status code {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    news_links = set()
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if "/news/" in href:
            full_link = href
            news_links.add(full_link)

    return news_links
