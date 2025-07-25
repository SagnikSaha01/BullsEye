file_path = "/Users/abhinavavasarala/Downloads/FinancialPhraseBank-v1.0/Sentences_75Agree.txt"

sentences = []
with open(file_path, "r", encoding="latin-1") as f:
    for line in f:
        line = line.strip()
        if "@" in line:
            sentence, sentiment = line.split("@")
            sentences.append((sentence.strip(), sentiment.strip()))


def evaluate_classifier(classifier, sentences, num_samples=10):
    correct = 0
    total = min(num_samples, len(sentences))
    for i in range(total):
        sentence, true_sentiment = sentences[i]
        pred = classifier(sentence)[0]['label'].lower()
        # Map FinBERT output to file sentiment format if needed
        # Example: FinBERT outputs 'positive', 'neutral', 'negative'
        # Your file may use 'positive', 'neutral', 'negative'
        if pred in true_sentiment.lower():
            correct += 1
    accuracy = correct / total
    print(f"Accuracy on first {total} samples: {accuracy:.2f}")
    return accuracy
