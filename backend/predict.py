
new_article = ""


\
def clean_text(text):
    import re, nltk
    from nltk.corpus import stopwords
    from nltk.stem import WordNetLemmatizer

    nltk.download("stopwords", quiet=True)
    nltk.download("wordnet", quiet=True)

    stop_words = set(stopwords.words("english"))
    lemmatizer = WordNetLemmatizer()

    text = text.lower()
    text = re.sub(r'[^a-z\s]', '', text)
    tokens = text.split()
    tokens = [lemmatizer.lemmatize(word) for word in tokens if word not in stop_words]
    return " ".join(tokens)

cleaned_article = clean_text(new_article)


X_new = vectorizer.transform([cleaned_article])  

prediction = model.predict(X_new)[0]  

print("Prediction:", "Price Up 📈" if prediction == 1 else "Price Down 📉")
