from fastapi import FastAPI
import requests
from dotenv import load_dotenv
import os
from newspaper import Article

load_dotenv()
api = FastAPI()


@api.get('/api/{stock_ticker}')
def index(stock_ticker):
    data = getStockData(stock_ticker)
    print(data)
    arr = findLinks(stock_ticker)
    getText(arr)
    return arr


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
    for url in links:
        try:
            article = Article(url)
            article.download()
            article.parse()
            #first 250 characters
            print(url + " " +article.text[:250])
        except Exception as e:
            print("unable to access: " + url)
    return 0

