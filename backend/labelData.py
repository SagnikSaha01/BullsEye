import pandas as pd
import requests
from dotenv import load_dotenv
import os

load_dotenv()
CURRENT_TICKER_TO_TRAIN = "TSLA"

data = requests.get(os.getenv("LOCAL_API_URL") + CURRENT_TICKER_TO_TRAIN)

df = pd.DataFrame(data.json())
print(df)