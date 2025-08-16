import os
import praw
from dotenv import load_dotenv
import logging

load_dotenv()
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_reddit_instance():
    # Get credentials from environment variables for security
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT", "SentimentApp/0.0.1")
    username = os.getenv("REDDIT_USERNAME")
    password = os.getenv("REDDIT_PASSWORD")

    # Try authenticated instance
    if all([client_id, client_secret, username, password]):
        try:
            reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                grant_type='password',
                username=username,
                password=password,
            )
            # This will raise an error if login fails
            reddit.user.me()
            logger.info("Authenticated Reddit instance")
            return reddit
        except Exception as auth_error:
            logger.warning(f"Authentication failed: {auth_error}")

    # Fallback to read-only mode
    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
    )
    reddit.read_only = True
    logger.info("Using read-only Reddit instance")
    return reddit

# Create a single Reddit instance to use throughout the app
reddit = get_reddit_instance()

class Reddit:
    def get_data(self, ticker: str):
        results = []
        try:
            subreddit = reddit.subreddit("stocks")
            # Use the search endpoint with a limit
            for submission in subreddit.search(ticker, limit=5):
                results.append({
                    "title": submission.title,
                    "url": submission.url,
                    "score": submission.score,
                    "subreddit": submission.subreddit.display_name,
                })

            if not results:
                logger.info(f"No Reddit results found for ticker: {ticker}")
        except Exception as e:
            error_msg = f"Reddit API error: {str(e)}"
            logger.error(error_msg)
            results.append({"error": error_msg})

        return results
