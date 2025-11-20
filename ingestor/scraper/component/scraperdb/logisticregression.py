import sqlite3
import sys
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    confusion_matrix,
    classification_report,
)
import joblib


DB_PATH = "./data/ingestor.db"

VIEW_NAME = "ml_features"
MODEL_PATH = "//data/logistic_model.pkl"


def load_data(db_path: str, view_name: str) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query(f"SELECT * FROM {view_name}", conn)
    finally:
        conn.close()
    return df


def train_logistic_model(df: pd.DataFrame):
    if df.empty:
        print("La vue ml_features est vide, impossible d'entraîner le modèle.")
        return None

    if "target_up" not in df.columns:
        print("La colonne 'target_up' n'existe pas dans la vue.")
        return None
    feature_cols = [
        "avg_volume",
        "avg_price",
        "avg_market_cap",
        "avg_circulating",
    ]
    df = df.dropna(subset=["target_up"])

    X = df[feature_cols].fillna(0)
    y = df["target_up"].astype(int)

    if len(df) < 5:
        print(f" Trop peu de lignes pour entraîner un modèle (n={len(df)}).")
        return None
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        shuffle=True,
        random_state=42,
    )
    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=1000),
    )

    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    print("\n=== Résultats régression logistique ===")
    print("Accuracy :", accuracy_score(y_test, y_pred))
    print("F1-score :", f1_score(y_test, y_pred))
    print("\nMatrice de confusion :")
    print(confusion_matrix(y_test, y_pred))
    print("\nClassification report :")
    print(classification_report(y_test, y_pred))

    return model


def main():
    print(f" Chargement des données depuis {DB_PATH} / vue {VIEW_NAME}...")
    df = load_data(DB_PATH, VIEW_NAME)

    print("Aperçu des données :")
    print(df.head())
    print("\nShape :", df.shape)

    model = train_logistic_model(df)
    if model is None:
        sys.exit(1)
    joblib.dump(model, MODEL_PATH)
    print(f"\n Modèle sauvegardé dans : {MODEL_PATH}")
    feature_cols = [
        "avg_volume",
        "avg_price",
        "avg_market_cap",
        "avg_circulating",
    ]
    X_demo = df[feature_cols].fillna(0).head()

    proba = model.predict_proba(X_demo)
    pred = model.predict(X_demo)

    print("\nExemple de prédictions sur les 5 premières fenêtres :")
    print("Proba [baisse, hausse] :")
    print(proba)
    print("Classe prédite (0=baisse ou stable, 1=hausse):")
    print(pred)


if __name__ == "__main__":
    main()
