import sqlite3
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix, classification_report
import joblib  # ⬅️ ajout

DB_PATH = "./data/ingestor.db"

conn = sqlite3.connect(DB_PATH)
df = pd.read_sql_query("SELECT * FROM ml_features", conn)
conn.close()

print("Aperçu des données :")
print(df.head())
print("\nShape :", df.shape)

feature_cols = [
    "avg_volume",
    "avg_price",
    "avg_market_cap",
    "avg_circulating",
]
df = df.dropna(subset=["target_up"])

X = df[feature_cols].fillna(0)
y = df["target_up"].astype(int)

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    shuffle=True,
    random_state=42,
)

model = make_pipeline(
    StandardScaler(),
    LogisticRegression(max_iter=1000)
)

model.fit(X_train, y_train)
y_pred = model.predict(X_test)

print("\n=== Résultats ===")
print("Accuracy :", accuracy_score(y_test, y_pred))
print("F1-score :", f1_score(y_test, y_pred))
print("\nMatrice de confusion :")
print(confusion_matrix(y_test, y_pred))
print("\nClassification report :")
print(classification_report(y_test, y_pred))

print("\nExemple de prédictions sur les 5 premières lignes :")
print("Proba P(baisse) / P(hausse) :")
y_proba = model.predict_proba(X.head())
print(y_proba)
print("Classe prédite :", model.predict(X.head()))
MODEL_PATH = "./data/logistic_model.pkl"
joblib.dump(model, MODEL_PATH)
print(f"\n Modèle sauvegardé dans {MODEL_PATH}")
