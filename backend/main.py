from fastapi import FastAPI
import requests
from dotenv import load_dotenv
import os
from newspaper import Article
import json

load_dotenv()
api = FastAPI()


@api.get('/api/{stock_ticker}')
def index(stock_ticker):
    #data = getStockData(stock_ticker)
    #print(data)
    arr = findLinks(stock_ticker)
    print(arr)
    # getText(arr)
    return arr


def getStockData(ticker):
    header = {'X-Finnhub-Token' : os.getenv("STOCK_DATA_TOKEN")}
    res = requests.get(os.getenv("STOCK_DATA_URL") + ticker, headers=header)
    return res.json()

def findLinks(ticker):
    outputJson = []
    searchQuery = "Stock news for " + ticker
    apiKey = os.getenv("NEWS_TOKEN")
    url = os.getenv("NEWS_URL").format(input=searchQuery, key = apiKey)
    res = requests.get(url).json()
    for i in range(0, 50):
        json.dumps(outputJson.append({
            "title" : res["articles"][i]["title"],
            "url" : res["articles"][i]["url"],
            "published" : res["articles"][i]["publishedAt"],
            "stock": ticker,
            "text": getText(res["articles"][i]["url"])
        }))
    return outputJson

def getText(url):
    #print(url)
    try:
        article = Article(url)
        article.download()
        article.parse()
        #first 250 characters
        #print(url + " " +article.text)
        return article.text
    except Exception as e:
        print("unable to access: " + url)
        return ""

