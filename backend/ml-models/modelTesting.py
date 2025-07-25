from backend.datasets.dataset import sentences, evaluate_classifier

from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")

classifier = pipeline("text-classification", model=model, tokenizer=tokenizer)

evaluate_classifier(classifier, sentences, 50)