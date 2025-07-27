from backend.ml_models.vader import classify_vader
from backend.datasets.dataset import sentences, evaluate_classifier
from backend.ml_models.ProsusAI_finbert import finbert_classifier

models = {
    "FinBERT": finbert_classifier,
    "VADER": classify_vader,
}

for name, model in models.items():
    print(f"\nEvaluating {name}")
    evaluate_classifier(model, sentences, 100)
