import pandas as pd
import yfinance as yf
import requests
from dotenv import load_dotenv
import re
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import datetime
import os
    
load_dotenv()
nltk.download("stopwords")
nltk.download("wordnet")


def cleanData(text):
 

    stop_words = set(stopwords.words("english"))
    lemmatizer = WordNetLemmatizer()
    
    text = text.lower()
   
    text = re.sub(r'[^a-z\s]', '', text)
    tokens = text.split()
    
    tokens = [lemmatizer.lemmatize(word) for word in tokens if word not in stop_words]
    return " ".join(tokens)

def get_stock_price(stock_symbol, published_date):

    publish_date = pd.to_datetime(published_date).date()

    data = yf.download(
        stock_symbol,
        start=pd.to_datetime(publish_date) - pd.Timedelta(days=3),
        end=pd.to_datetime(publish_date) + pd.Timedelta(days=3),
        interval="1d",
        progress=False
    )

    price_today = None
    price_next_day = None


    for i, ts in enumerate(data.index):
        ts_date = ts.date()  
        if ts_date >= publish_date:
            price_today = data.iloc[i]["Close"]
            if i + 1 < len(data):
                price_next_day = data.iloc[i + 1]["Close"]
            break

    if price_today is None or price_next_day is None:
        return None

    return int(price_next_day > price_today)


CURRENT_TICKER_TO_TRAIN = "AAPL"

data = requests.get(os.getenv("LOCAL_API_URL") + CURRENT_TICKER_TO_TRAIN)
df = pd.DataFrame(data.json())

df["text"] = df["text"].apply(cleanData)
df['label'] = df.apply(lambda row: 1 if get_stock_price("TSLA", row['published']) else 0, axis=1)

print(df)
df.to_csv("articlesAAPL.csv", index=False)





