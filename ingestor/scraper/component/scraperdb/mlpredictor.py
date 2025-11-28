# ingestor/scraper/component/scraperdb/ml_predictor.py

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import joblib
import mysql.connector
import pandas as pd

from .linearregression import (
    MYSQL_CONFIG,
    FEATURE_COLS,
    _parse_window_label,
)

BASE_DIR = Path(__file__).parent

REG_MODEL_PATH = BASE_DIR / "data" / "linear_model.pkl"
CLF_MODEL_PATH = BASE_DIR / "data" / "classifier_target_up.pkl"

try:
    reg_model = joblib.load(REG_MODEL_PATH)
    clf_model = joblib.load(CLF_MODEL_PATH)
    print(f"[ML] Modèles chargés depuis {REG_MODEL_PATH} et {CLF_MODEL_PATH}")
except Exception as e:
    print(f"[ML] ERREUR chargement modèles : {e}")
    reg_model = None
    clf_model = None


def predict_symbol_window(
    symbol: str,
    date_start: Optional[str | datetime] = None,
) -> Dict[str, Any]:
    """
    Prédit le mouvement d'un symbole sur une fenêtre d'une heure (ou autre, selon window_label).

    Entrées :
      - symbol : ex "BTC", "ETH", "SOL"
      - date_start : début de la fenêtre. Si :
          * None      -> on prend la DERNIÈRE fenêtre delta pour ce symbol
          * str       -> parsée en ISO (ex '2025-11-20T12:00:00')
          * datetime  -> utilisée telle quelle

    Sortie : dict au format style API :
    {
      "success": True/False,
      "message": "...",
      "data": {
          "symbol": "...",
          "window_label": "1h",
          "date_start": ...,
          "date_end": ...,
          "price_now": ...,
          "delta_pct_pred": ...,
          "delta_pct_real": ...,
          "prob_up": ...,
          "price_pred": ...,
          "features_used": { ... }
      }
    }
    """

    # Vérifier que les modèles sont bien chargés
    if reg_model is None or clf_model is None:
        return {
            "success": False,
            "message": "Modèles ML non chargés côté backend",
            "data": None,
        }

    # Normalisation du symbol
    symbol = symbol.upper().strip()

    # Parsing de la date_start si besoin
    parsed_date_start: Optional[datetime] = None
    if isinstance(date_start, datetime):
        parsed_date_start = date_start
    elif isinstance(date_start, str):
        try:
            ds = date_start.replace("Z", "+00:00")
            parsed_date_start = datetime.fromisoformat(ds)
        except Exception as e:
            return {
                "success": False,
                "message": f"Format de date_start invalide : {date_start} ({e})",
                "data": None,
            }

    # Connexion DB
    try:
        con = mysql.connector.connect(**MYSQL_CONFIG)
    except Exception as e:
        return {
            "success": False,
            "message": f"Erreur de connexion MySQL : {e}",
            "data": None,
        }

    try:
        # 1) Récupérer la ligne delta pour ce symbole + date_start (ou dernière)
        if parsed_date_start is None:
            delta_query = """
                SELECT symbol, date_start, date_end, window_label, delta_pct
                FROM delta
                WHERE symbol = %s
                ORDER BY date_start DESC
                LIMIT 1
            """
            delta_df = pd.read_sql(delta_query, con, params=(symbol,))
        else:
            delta_query = """
                SELECT symbol, date_start, date_end, window_label, delta_pct
                FROM delta
                WHERE symbol = %s
                  AND date_start = %s
                ORDER BY date_start DESC
                LIMIT 1
            """
            delta_df = pd.read_sql(delta_query, con, params=(symbol, parsed_date_start))

        if delta_df.empty:
            return {
                "success": False,
                "message": f"Aucune fenêtre delta trouvée pour {symbol} "
                           f"{'(dernière fenêtre)' if parsed_date_start is None else f'avec date_start={parsed_date_start}'}",
                "data": None,
            }

        drow = delta_df.iloc[0]
        dt_start = pd.to_datetime(drow["date_start"])
        window_label = drow["window_label"]
        win_delta = _parse_window_label(window_label)
        dt_end = dt_start + win_delta
        delta_pct_real = float(drow["delta_pct"])

        # 2) Récupérer les articles de ce symbole dans la fenêtre [start, end)
        art_query = """
            SELECT fetched_at, price, market_cap, coin_circulating, volume_24h
            FROM article
            WHERE symbol = %s
              AND fetched_at >= %s
              AND fetched_at <  %s
        """
        art_df = pd.read_sql(art_query, con, params=(symbol, dt_start, dt_end))

        if art_df.empty:
            return {
                "success": False,
                "message": f"Aucun article trouvé pour {symbol} entre {dt_start} et {dt_end}",
                "data": None,
            }

        # Cast des colonnes numériques
        art_df["price"] = pd.to_numeric(art_df["price"], errors="coerce")
        art_df["market_cap"] = pd.to_numeric(art_df["market_cap"], errors="coerce")
        art_df["coin_circulating"] = pd.to_numeric(art_df["coin_circulating"], errors="coerce")
        art_df["volume_24h"] = pd.to_numeric(art_df["volume_24h"], errors="coerce")

        art_df = art_df.dropna(subset=["price"])
        if art_df.empty:
            return {
                "success": False,
                "message": f"Aucun article exploitable (price NULL) pour {symbol} entre {dt_start} et {dt_end}",
                "data": None,
            }

        # 3) Calcul des features (mêmes que pour le training)
        nb_articles = int(len(art_df))
        avg_price = float(art_df["price"].mean())
        avg_market_cap = float(art_df["market_cap"].mean()) if art_df["market_cap"].notna().any() else 0.0
        avg_circulating = float(art_df["coin_circulating"].mean()) if art_df["coin_circulating"].notna().any() else 0.0
        avg_volume = float(art_df["volume_24h"].mean()) if art_df["volume_24h"].notna().any() else 0.0

        art_df = art_df.sort_values("fetched_at")
        price_now = float(art_df["price"].iloc[-1])

        features_used = {
            "nb_articles": nb_articles,
            "avg_volume": avg_volume,
            "avg_price": avg_price,
            "avg_market_cap": avg_market_cap,
            "avg_circulating": avg_circulating,
        }

        # 4) Construire X pour le modèle
        X = pd.DataFrame([features_used])

        # 5) Prédictions
        delta_pred = float(reg_model.predict(X)[0])
        prob_up = float(clf_model.predict_proba(X)[0, 1])

        price_pred = price_now * (1.0 + delta_pred / 100.0)

        return {
            "success": True,
            "message": "Prédiction calculée avec succès",
            "data": {
                "symbol": symbol,
                "window_label": window_label,
                "date_start": dt_start,
                "date_end": dt_end,
                "price_now": price_now,
                "delta_pct_pred": delta_pred,
                "delta_pct_real": delta_pct_real,  # pour debug / comparaison
                "prob_up": prob_up,
                "price_pred": price_pred,
                "features_used": features_used,
            },
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Erreur lors de la prédiction : {e}",
            "data": None,
        }
    finally:
        con.close()
