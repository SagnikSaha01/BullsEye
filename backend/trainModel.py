import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report


csv_files= ["articlesAAPL.csv", "articlesUNH.csv", "articlesTSLA.csv", "articlesMSFT.csv", "articlesAMD.csv", "articlesNVDA.csv"]

dfs = [pd.read_csv(file) for file in csv_files]


df = pd.concat(dfs, ignore_index=True)

df = df.dropna(subset=["text"])


X = df["text"]   
y = df["label"]  


X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)


vectorizer = TfidfVectorizer(max_features=5000)
X_train_tfidf = vectorizer.fit_transform(X_train)
X_test_tfidf = vectorizer.transform(X_test)


model = LogisticRegression(max_iter=1000)
model.fit(X_train_tfidf, y_train)


y_pred = model.predict(X_test_tfidf)


print("Accuracy:", accuracy_score(y_test, y_pred))
print("\nClassification Report:\n", classification_report(y_test, y_pred))
