from fastapi import FastAPI
import requests
from dotenv import load_dotenv
import os

load_dotenv()
api = FastAPI()


@api.get('/api/{stock_ticker}')
def index(stock_ticker):
    data = getStockData(stock_ticker)
    print(data)
    return findLinks(stock_ticker)


def getStockData(ticker):
    header = {'X-Finnhub-Token' : os.getenv("STOCK_DATA_TOKEN")}
    res = requests.get(os.getenv("STOCK_DATA_URL") + ticker, headers=header)
    return res.json()

def findLinks(ticker):
    newsLinks = []
    searchQuery = "Stock news for " + ticker
    apiKey = os.getenv("NEWS_TOKEN")
    url = os.getenv("NEWS_URL").format(input=searchQuery, key = apiKey)
    res = requests.get(url).json()
    for i in range(0, 20):
        newsLinks.append(res["articles"][i]["url"])
    return newsLinks

# TODO: read links and extract words
def getText(links):
    return 0

