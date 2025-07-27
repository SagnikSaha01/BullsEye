from backend.datasets.dataset import sentences, evaluate_classifier

from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")

finbert_classifier = pipeline("text-classification", model=model, tokenizer=tokenizer)

# evaluate_classifier(finbert_classifier, sentences, 100)