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

def round_probs(d, places=3):
    return {k: round(float(v), places) for k, v in d.items()}

def finbert_probs(text_or_texts):
    pipe = _get_pipe()

    # For HF >= 4.41 use top_k=None; for older versions use return_all_scores=True
    out = pipe(
        text_or_texts,
        truncation=True,
        padding=True,
        top_k=None,  # or: return_all_scores=True
        max_length=512,
    )

    def scores_to_dict(one):
        # one looks like: [{'label':'positive','score':0.94}, ...]
        d = {e["label"].lower(): float(e["score"]) for e in one}
        # ensure consistent keys
        for k in ("positive", "neutral", "negative"):
            d.setdefault(k, 0.0)
        return d

    if isinstance(text_or_texts, str):
        return scores_to_dict(out)
    else:
        return [scores_to_dict(item) for item in out]