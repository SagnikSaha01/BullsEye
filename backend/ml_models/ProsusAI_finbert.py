# from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
# tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
# model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")

# finbert_classifier = pipeline("text-classification", model=model, tokenizer=tokenizer)

from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification

_pipe = None

def _get_pipe():
    global _pipe
    if _pipe is None:
        tokenizer = AutoTokenizer.from_pretrained(
            "ProsusAI/finbert",
            model_max_length=512,  # cap
            truncation=True
        )
        model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
        _pipe = pipeline(
            "text-classification",
            model=model,
            tokenizer=tokenizer
        )
    return _pipe

def finbert_classifier(text: str):
    pipe = _get_pipe()
    # Force truncation/padding on every call; works for str or List[str]
    return pipe(text or "", truncation=True, max_length=512, padding=True)