from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from backend.datasets.dataset import sentences, evaluate_classifier


vader_analyzer = SentimentIntensityAnalyzer()

def classify_vader(text):
    score = vader_analyzer.polarity_scores(text)["compound"]
    if score >= 0.05:
        return [{"label": "positive"}]
    elif score <= -0.05:
        return [{"label": "negative"}]
    else:
        return [{"label": "neutral"}]
    
# evaluate_classifier(classify_vader, sentences, num_samples=100)