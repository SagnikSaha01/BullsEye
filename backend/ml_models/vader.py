from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


vader_analyzer = SentimentIntensityAnalyzer()

_vader = None
def _get_vader():
    global _vader
    if _vader is None:
        _vader = SentimentIntensityAnalyzer()
    return _vader

def classify_vader(text):
    score =  _get_vader().polarity_scores(text)["compound"]
    if score >= 0.05:
        return [{"label": "positive"}]
    elif score <= -0.05:
        return [{"label": "negative"}]
    else:
        return [{"label": "neutral"}]
    
# evaluate_classifier(classify_vader, sentences, num_samples=100)