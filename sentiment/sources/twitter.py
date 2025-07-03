# sentiment/sources/twitter.py

import tweepy

class Twitter:
    def __init__(self):
        # Replace this string with your actual Bearer Token (keep it secret!)
        self.bearer_token = "cLNCX2TIezKxUoBCrFsFw70OV"

        self.client = tweepy.Client(bearer_token=self.bearer_token)

    def get_data(self, ticker: str):
        query = f"${ticker} -is:retweet lang:en"
        try:
            tweets = self.client.search_recent_tweets(query=query, max_results=10, tweet_fields=['created_at','text'])
            if tweets.data:
                return [{"tweet": tweet.text, "created_at": tweet.created_at.isoformat()} for tweet in tweets.data]
            else:
                return []
        except Exception as e:
            return [{"error": str(e)}]
