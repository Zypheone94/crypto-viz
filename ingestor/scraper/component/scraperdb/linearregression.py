import sys
import pandas as pd
import mysql.connector
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (
    r2_score,
    mean_absolute_error,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
import joblib

MYSQL_CONFIG = {
    "host": "localhost",
    "user": "ingestor_user",
    "password": "password123",
    "database": "ingestor",
}
FEATURE_COLS = [
    "nb_articles",
    "avg_volume",
    "avg_price",
    "avg_market_cap",
    "avg_circulating",
]

MODEL_PATH = "./data/linear_model.pkl"
from datetime import timedelta

def _parse_window_label(label: str) -> timedelta:
    if not label:
        return timedelta(hours=1)

    s = label.strip().lower()

    try:
        if s.endswith("h"):
            value = float(s[:-1])
            return timedelta(hours=value)
        if s.endswith("m"):
            value = float(s[:-1])
            return timedelta(minutes=value)
        if s.endswith("d"):
            value = float(s[:-1])
            return timedelta(days=value)
    except ValueError:
        pass
    return timedelta(hours=1)


def load_features_from_tables() -> pd.DataFrame:
    """ Ici j'ai du recontrsuire l'équivalent de la vue ml_features (voir initdb.Sql) car celle ci fait crash la db
    a cause de la masse de données (on a des joins + agrégats AVG) donc en faisant a la main, étape par étape
    ca permet de ne pas finir avec un timeout ou un memory leak.
    """
    conn = mysql.connector.connect(**MYSQL_CONFIG)
    try:
        print("Chargement des tables delta et article...")

        delta_df = pd.read_sql(
            """
            SELECT
                symbol,
                date_start,
                date_end,
                window_label,
                delta_pct
            FROM delta
            """,
            conn,
        )

        article_df = pd.read_sql(
            """
            SELECT
                symbol,
                fetched_at,
                price,
                market_cap,
                coin_circulating,
                volume_24h
            FROM article
            """,
            conn,
        )
    finally:
        conn.close()

    if delta_df.empty:
        print("Table delta vide, impossible de construire les features.")
        return pd.DataFrame()

    if article_df.empty:
        print("Table article vide, impossible de construire les features.")
        return pd.DataFrame()

    delta_df["date_start"] = pd.to_datetime(delta_df["date_start"])
    article_df["fetched_at"] = pd.to_datetime(article_df["fetched_at"])

    print("Préparation des articles par symbol...")
    article_df = article_df.sort_values(["symbol", "fetched_at"])
    articles_by_symbol: dict[str, pd.DataFrame] = {
        sym: grp for sym, grp in article_df.groupby("symbol")
    }

    features = []

    print("Construction des features delta par delta...")
    for sym, deltas_sym in delta_df.groupby("symbol"):
        articles_sym = articles_by_symbol.get(sym)
        if articles_sym is None or articles_sym.empty:
            continue

        fetched = articles_sym["fetched_at"]
        price = articles_sym["price"]
        mcap = articles_sym["market_cap"]
        circ = articles_sym["coin_circulating"]
        vol = articles_sym["volume_24h"]

        for row in deltas_sym.itertuples(index=False):
            dt_start = row.date_start
            win_delta = _parse_window_label(row.window_label)
            dt_end = dt_start + win_delta
            mask = (fetched >= dt_start) & (fetched < dt_end)
            if not mask.any():
                continue

            sub_price = price[mask]
            sub_mcap = mcap[mask]
            sub_circ = circ[mask]
            sub_vol = vol[mask]

            features.append(
                {
                    "symbol": row.symbol,
                    "date_start": dt_start,
                    "date_end": dt_end,
                    "delta_pct": row.delta_pct,
                    "nb_articles": int(mask.sum()),
                    "avg_price": float(sub_price.mean()) if not sub_price.empty else None,
                    "avg_market_cap": float(sub_mcap.mean()) if not sub_mcap.empty else None,
                    "avg_circulating": float(sub_circ.mean()) if not sub_circ.empty else None,
                    "avg_volume": float(sub_vol.mean()) if not sub_vol.empty else None,
                }
            )

    if not features:
        print("Aucune fenêtre delta n'a d'articles associés.")
        return pd.DataFrame()

    features_df = pd.DataFrame(features)
    features_df["target_delta_pct"] = features_df["delta_pct"]
    features_df["target_up"] = (features_df["delta_pct"] > 0).astype(int)

    return features_df

def train_linear_model(df: pd.DataFrame):
    if df.empty:
        print("DataFrame de features vide, impossible d'entraîner le modèle.")
        return None

    if "target_delta_pct" not in df.columns:
        print("La colonne 'target_delta_pct' n'existe pas dans les données.")
        return None
    df = df.dropna(subset=["target_delta_pct"])
    X_raw = df[FEATURE_COLS]
    mask_valid_features = X_raw.notna().any(axis=1)
    df = df[mask_valid_features]
    X_raw = X_raw[mask_valid_features]
    y = df["target_delta_pct"].astype(float)
    mask_target = y.between(-1000, 1000)
    df = df[mask_target]
    X_raw = X_raw[mask_target]
    y = y[mask_target]

    if len(df) < 10:
        print(f"Trop peu de lignes pour entraîner un modèle (n={len(df)}).")
        return None
    X = X_raw.infer_objects(copy=False).fillna(0)
    X_temp, X_test, y_temp, y_test = train_test_split(
        X,
        y,
        test_size=0.10,
        shuffle=True,
        random_state=42,
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp,
        y_temp,
        test_size=2/9,
        shuffle=True,
        random_state=42,
    )
    model = make_pipeline(
        StandardScaler(),
        LinearRegression(),
    )
    model.fit(X_train, y_train)
    y_val_pred = model.predict(X_val)
    print("R² (validation) :", r2_score(y_val, y_val_pred))
    print("MAE (validation):", mean_absolute_error(y_val, y_val_pred))
    y_test_pred = model.predict(X_test)
    print("R² (test) :", r2_score(y_test, y_test_pred))
    print("MAE (test):", mean_absolute_error(y_test, y_test_pred))

    return model

def train_classifier(df: pd.DataFrame):
    """
    Modèle de classification binaire sur target_up (0/1) :
    1 = delta_pct > 0, 0 = delta_pct <= 0
    Split 70 / 20 / 10 comme pour la régression.
    """

    X_raw = df[FEATURE_COLS]
    mask_valid_features = X_raw.notna().any(axis=1)
    df = df[mask_valid_features]
    X_raw = X_raw[mask_valid_features]
    y = df["target_up"].astype(int)
    if "target_delta_pct" in df.columns:
        mask_target = df["target_delta_pct"].between(-1000, 1000)
        df = df[mask_target]
        X_raw = X_raw[mask_target]
        y = y[mask_target]

    if len(df) < 10:
        print(f"Trop peu de lignes pour entraîner un classifieur (n={len(df)}).")
        return None

    X = X_raw.infer_objects(copy=False).fillna(0)
    X_temp, X_test, y_temp, y_test = train_test_split(
        X,
        y,
        test_size=0.10,
        shuffle=True,
        random_state=42,
        stratify=y,
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp,
        y_temp,
        test_size=2/9,
        shuffle=True,
        random_state=42,
        stratify=y_temp,
    )

    clf = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=1000),
    )
    clf.fit(X_train, y_train)
    y_val_pred = clf.predict(X_val)
    print("Accuracy (validation) :", accuracy_score(y_val, y_val_pred))
    print("F1 (val)       :", f1_score(y_val, y_val_pred))

    y_test_pred = clf.predict(X_test)
    print("Accuracy (test) :", accuracy_score(y_test, y_test_pred))
    print("F1 (test)       :", f1_score(y_test, y_test_pred))


    return clf

def main():
    df = load_features_from_tables()
    model = train_linear_model(df)
    if model is None:
        sys.exit(1)

    joblib.dump(model, MODEL_PATH)
    print(f"\nModèle sauvegardé dans : {MODEL_PATH}")

    X_demo = df[FEATURE_COLS].infer_objects(copy=False).fillna(0).head()

    y_demo_pred = model.predict(X_demo)
    print(y_demo_pred)
    clf = train_classifier(df)
    if clf is not None:
        joblib.dump(clf, "./data/classifier_target_up.pkl")
        y_demo_proba = clf.predict_proba(X_demo)[:, 1]
        print(y_demo_proba)





if __name__ == "__main__":
    main()
