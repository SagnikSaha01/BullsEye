import requests
import string
import json
'''
authUrl = "https://www.reddit.com/api/v1/access_token"
username = "Zl-3Jfr6rfWIm1AQvqdbNw"
password = "lxR1lQusSfj-rQWfnZSqz5aCgE0u8g"

data = {
    "grant_type": "password",
    "username": "Responsible_Stand844",
    "password": "sagnik123"
}

res = requests.post(authUrl, auth=(username, password), data=data).json()
token = res['access_token']
'''
#prints out the auth token needed for authenticated requests (basicaly gives more api calls without rate limit)
token = "eyJhbGciOiJSUzI1NiIsImtpZCI6IlNIQTI1NjpzS3dsMnlsV0VtMjVmcXhwTU40cWY4MXE2OWFFdWFyMnpLMUdhVGxjdWNZIiwidHlwIjoiSldUIn0.eyJzdWIiOiJ1c2VyIiwiZXhwIjoxNzU1Mzc3MzE3LjY1NTQ1MSwiaWF0IjoxNzU1MjkwOTE3LjY1NTQ1MSwianRpIjoiejE4N0J4S2NrRkwzUGRBZjhELW5TNFlvMnR5X2FRIiwiY2lkIjoiWmwtM0pmcjZyZldJbTFBUXZxZGJOdyIsImxpZCI6InQyX2R6MjNnNGt5IiwiYWlkIjoidDJfZHoyM2c0a3kiLCJsY2EiOjE2MjkyMTI1MDgwMDAsInNjcCI6ImVKeUtWdEpTaWdVRUFBRF9fd056QVNjIiwiZmxvIjo5fQ.k10S84H0Es5BZXDOMGFq0n0AknyW3SmMxgLcZMtoEud6K61CYIBbpYAmqnDE_DojlyJXiuKIakigbme-0InG2mnczSOjkC9nm8qaftAnU_ojK3uPsGqxMJlH4y_HKZIPE7TFPgO5nExcJRGccCmQPhHjmvNL78o5fA_mvsbOPVezwazzHxnYNOLPQuHd0bN4Xklyh4Aoj1C0ORa4jnQYlGsLFkhSvE1NB8QBnd__CMPr72w96OJA_5ksQ4X7AvSD8YXEOjUgK6c1lwXxj-OgxYfZ15L2FCjmIdv5lVvrWpl68f0j2_k-rFlHUb-GomWPCT9846veW7sA1_RnWMV3LA"
print(token)
auth_header = {
    "Authorization": f"bearer {token}",
}

subreddit = "stocks"
query = "UNH"

search_url = f"https://oauth.reddit.com/r/{subreddit}/search"
params = {
    "q": query,
    "restrict_sr": True,   # only in this subreddit
    "sort": "new",
    "limit": 3             # get the top matching post
}

search_res = requests.get(search_url, headers=auth_header, params=params)
search_data = search_res.json()

results_array = []

for post in search_data["data"]["children"]:
    post_data = post["data"]
    post_id = post_data["id"]
    title = post_data["title"]

    # Fetch post content
    comments_url = f"https://oauth.reddit.com/r/{subreddit}/comments/{post_id}"
    post_res = requests.get(comments_url, headers=auth_header)
    post_content = post_res.json()[0]["data"]["children"][0]["data"].get("selftext", "")

    # Clean text: remove punctuation, lowercase
    translator = str.maketrans("", "", string.punctuation)
    clean_text = post_content.translate(translator)
    clean_text = " ".join(clean_text.split()).lower()  # single string of words

    # Add to results array as a dict
    results_array.append({
        "title": title,
        "text": clean_text
    })

# ==== 5. PRINT RESULT ====
print(results_array)