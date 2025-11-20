"""
Random Forest pour prédiction de tendance crypto (hausse/baisse).
Features: price, volume_24h, market_cap, moving averages
Target: 1 si prix monte dans la prochaine fenêtre, 0 sinon
"""
import os
import mysql.connector
from pathlib import Path
from typing import Dict, Any, List, Tuple
import pickle

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix


MODEL_DIR = Path(os.getenv("MODEL_DIR", "/app/ingestor/builder/algo/models"))
MODEL_PATH = MODEL_DIR / "random_forest.pkl"


def load_data_from_db(symbol: str | None = None, limit: int = 10000) -> pd.DataFrame:
    """
    Charge les données depuis MySQL et calcule les features pour le Random Forest.
    
    Returns: DataFrame avec colonnes [symbol, fetched_at, price, volume_24h, market_cap, 
                                      price_change, target]
    """
    con = mysql.connector.connect(
        host="host.docker.internal",
        user="ingestor_user",
        password="password123",
        database="ingestor"
    )
    
    where_clause = ""
    params: List[Any] = []
    if symbol:
        where_clause = "WHERE symbol = %s"
        params.append(symbol)
    
    query = f"""
        SELECT 
            symbol,
            fetched_at,
            price,
            volume_24h,
            market_cap,
            coin_circulating
        FROM article
        {where_clause}
        ORDER BY symbol, fetched_at ASC
        LIMIT %s
    """
    params.append(limit)
    
    df = pd.read_sql_query(query, con, params=params)
    con.close()
    
    if df.empty:
        return df
    
    # Nettoyer et convertir les types
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    df['volume_24h'] = pd.to_numeric(df['volume_24h'], errors='coerce')
    df['market_cap'] = pd.to_numeric(df['market_cap'], errors='coerce')
    df['coin_circulating'] = pd.to_numeric(df['coin_circulating'], errors='coerce')
    
    # Supprimer les lignes avec prix manquant
    df = df.dropna(subset=['price'])
    
    # Calculer les features par symbole
    df = df.sort_values(['symbol', 'fetched_at'])
    
    # Moving averages (fenêtre courte et longue)
    df['price_ma_short'] = df.groupby('symbol')['price'].transform(lambda x: x.rolling(5, min_periods=1).mean())
    df['price_ma_long'] = df.groupby('symbol')['price'].transform(lambda x: x.rolling(20, min_periods=1).mean())
    
    # Volume moving average
    df['volume_ma'] = df.groupby('symbol')['volume_24h'].transform(lambda x: x.rolling(5, min_periods=1).mean())
    
    # Price change (variation depuis la ligne précédente)
    df['price_change'] = df.groupby('symbol')['price'].pct_change()
    
    # Target: 1 si le prix monte à la prochaine observation, 0 sinon
    df['price_next'] = df.groupby('symbol')['price'].shift(-1)
    df['target'] = (df['price_next'] > df['price']).astype(int)
    
    # Supprimer la dernière ligne par symbole (pas de target)
    df = df.dropna(subset=['target'])
    
    # Remplir les NaN restants avec 0
    df = df.fillna(0)
    
    return df


def prepare_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Prépare X (features) et y (target) pour l'entraînement.
    """
    feature_cols = [
        'price', 'volume_24h', 'market_cap', 'coin_circulating',
        'price_ma_short', 'price_ma_long', 'volume_ma', 'price_change'
    ]
    
    X = df[feature_cols].copy()
    y = df['target'].copy()
    
    # Remplacer inf par 0
    X = X.replace([np.inf, -np.inf], 0)
    
    return X, y


def train_model(
    symbol: str | None = None,
    n_estimators: int = 100,
    max_depth: int | None = 10,
    test_size: float = 0.2,
    random_state: int = 42
) -> Dict[str, Any]:
    """
    Entraîne un Random Forest Classifier sur les données de la base.
    
    Returns: dict avec model, metrics, feature_importance
    """
    # Charger les données
    df = load_data_from_db(symbol=symbol, limit=10000)
    
    if df.empty or len(df) < 50:
        raise ValueError(f"Pas assez de données pour entraîner (rows={len(df)})")
    
    X, y = prepare_features(df)
    
    # Split train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )
    
    # Entraîner le modèle
    model = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        random_state=random_state,
        n_jobs=-1
    )
    model.fit(X_train, y_train)
    
    # Prédictions
    y_pred_train = model.predict(X_train)
    y_pred_test = model.predict(X_test)
    
    # Métriques
    metrics = {
        "train": {
            "accuracy": float(accuracy_score(y_train, y_pred_train)),
            "precision": float(precision_score(y_train, y_pred_train, zero_division=0)),
            "recall": float(recall_score(y_train, y_pred_train, zero_division=0)),
            "f1": float(f1_score(y_train, y_pred_train, zero_division=0)),
        },
        "test": {
            "accuracy": float(accuracy_score(y_test, y_pred_test)),
            "precision": float(precision_score(y_test, y_pred_test, zero_division=0)),
            "recall": float(recall_score(y_test, y_pred_test, zero_division=0)),
            "f1": float(f1_score(y_test, y_pred_test, zero_division=0)),
        },
        "confusion_matrix": confusion_matrix(y_test, y_pred_test).tolist(),
        "train_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
    }
    
    # Feature importance
    feature_importance = {
        col: float(imp) 
        for col, imp in zip(X.columns, model.feature_importances_)
    }
    
    return {
        "model": model,
        "metrics": metrics,
        "feature_importance": feature_importance,
        "feature_names": list(X.columns),
        "symbol": symbol or "ALL",
    }


def save_model(result: Dict[str, Any], path: Path | None = None) -> None:
    """Sauvegarde le modèle entraîné sur disque."""
    if path is None:
        path = MODEL_PATH
    
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'wb') as f:
        pickle.dump(result, f)
    
    print(f"Model saved to {path}")


def load_model(path: Path | None = None) -> Dict[str, Any]:
    """Charge un modèle depuis le disque."""
    if path is None:
        path = MODEL_PATH
    
    if not path.exists():
        raise FileNotFoundError(f"Model not found at {path}")
    
    with open(path, 'rb') as f:
        result = pickle.load(f)
    
    return result


def predict(symbol: str, recent_count: int = 1) -> Dict[str, Any]:
    """
    Prédit la tendance (hausse/baisse) pour les dernières observations d'un symbole.
    
    Args:
        symbol: Symbole crypto (ex: BTC)
        recent_count: Nombre de dernières lignes à prédire
    
    Returns: dict avec predictions, probabilities, features
    """
    # Charger le modèle
    try:
        result = load_model()
        model = result["model"]
        feature_names = result["feature_names"]
    except FileNotFoundError:
        raise ValueError("Model not trained yet. Train first via POST /algo/random-forest/train")
    
    # Charger les dernières données pour ce symbole
    df = load_data_from_db(symbol=symbol, limit=1000)
    
    if df.empty:
        raise ValueError(f"No data found for symbol {symbol}")
    
    # Prendre les N dernières lignes
    df_recent = df.tail(recent_count).copy()
    
    X, _ = prepare_features(df_recent)
    
    # S'assurer que les colonnes matchent
    X = X[feature_names]
    
    # Prédire
    predictions = model.predict(X)
    probabilities = model.predict_proba(X)
    
    results = []
    for i, (idx, row) in enumerate(df_recent.iterrows()):
        results.append({
            "fetched_at": row.get("fetched_at"),
            "price": float(row.get("price", 0)),
            "prediction": int(predictions[i]),
            "prediction_label": "HAUSSE" if predictions[i] == 1 else "BAISSE",
            "probability_baisse": float(probabilities[i][0]),
            "probability_hausse": float(probabilities[i][1]),
            "features": {col: float(X.iloc[i][col]) for col in feature_names}
        })
    
    return {
        "symbol": symbol,
        "predictions": results
    }


if __name__ == "__main__":
    # Test: entraîner et sauvegarder un modèle
    print("Training Random Forest model...")
    result = train_model(symbol=None, n_estimators=50, max_depth=8)
    
    print("\n=== Metrics ===")
    print(f"Train accuracy: {result['metrics']['train']['accuracy']:.3f}")
    print(f"Test accuracy: {result['metrics']['test']['accuracy']:.3f}")
    print(f"Test F1: {result['metrics']['test']['f1']:.3f}")
    
    print("\n=== Feature Importance ===")
    for feat, imp in sorted(result['feature_importance'].items(), key=lambda x: -x[1])[:5]:
        print(f"{feat}: {imp:.4f}")
    
    # Sauvegarder
    save_model(result)
    print("\nModel saved successfully!")
