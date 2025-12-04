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
    max_windows_to_try: int = 50,
) -> Dict[str, Any]:

    if reg_model is None or clf_model is None:
        return {
            "success": False,
            "message": "Modèles ML non chargés côté backend",
            "data": None,
        }

    symbol = symbol.upper().strip()

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
    try:
        con = mysql.connector.connect(**MYSQL_CONFIG)
    except Exception as e:
        return {
            "success": False,
            "message": f"Erreur de connexion MySQL : {e}",
            "data": None,
        }

    try:
        if parsed_date_start is None:
            delta_query = f"""
                SELECT symbol, date_start, date_end, window_label, delta_pct
                FROM delta
                WHERE symbol = %s
                ORDER BY date_start DESC
                LIMIT {max_windows_to_try}
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
                "message": (
                    f"Aucune fenêtre delta trouvée pour {symbol} "
                    f"{'(dernières fenêtres)' if parsed_date_start is None else f'avec date_start={parsed_date_start}'}"
                ),
                "data": None,
            }

        last_error_msg = None
        for _, drow in delta_df.iterrows():
            dt_start = pd.to_datetime(drow["date_start"])
            window_label = drow["window_label"]
            win_delta = _parse_window_label(window_label)
            dt_end = dt_start + win_delta

            delta_pct_real = float(drow["delta_pct"])
            art_query = """
                SELECT fetched_at, price, market_cap, coin_circulating, volume_24h
                FROM article
                WHERE symbol = %s
                  AND fetched_at >= %s
                  AND fetched_at <  %s
            """
            art_df = pd.read_sql(art_query, con, params=(symbol, dt_start, dt_end))

            if art_df.empty:
                last_error_msg = (
                    f"Aucun article trouvé pour {symbol} entre {dt_start} et {dt_end} "
                    f"(fenêtre {window_label})"
                )
                continue

            art_df["price"] = pd.to_numeric(art_df["price"], errors="coerce")
            art_df["market_cap"] = pd.to_numeric(art_df["market_cap"], errors="coerce")
            art_df["coin_circulating"] = pd.to_numeric(art_df["coin_circulating"], errors="coerce")
            art_df["volume_24h"] = pd.to_numeric(art_df["volume_24h"], errors="coerce")

            art_df = art_df.dropna(subset=["price"])
            if art_df.empty:
                last_error_msg = (
                    f"Aucun article exploitable (price NULL) pour {symbol} "
                    f"entre {dt_start} et {dt_end} (fenêtre {window_label})"
                )
                continue
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

            X = pd.DataFrame([features_used])
            delta_pred = float(reg_model.predict(X)[0])
            prob_up = float(clf_model.predict_proba(X)[0, 1])

            price_pred = price_now * (1.0 + delta_pred / 100.0)
            target_ts = dt_end

            return {
                "success": True,
                "message": "Prédiction calculée avec succès",
                "data": {
                    "symbol": symbol,
                    "window_label": window_label,
                    "date_start": dt_start,
                    "date_end": dt_end,
                    "target_ts": target_ts,
                    "price_now": price_now,
                    "delta_pct_pred": delta_pred,
                    "delta_pct_real": delta_pct_real,
                    "prob_up": prob_up,
                    "price_pred": price_pred,
                    "features_used": features_used,
                },
            }
        return {
            "success": False,
            "message": last_error_msg
            or f"Aucune fenêtre delta exploitable pour {symbol} (pas d'articles dans les {max_windows_to_try} dernières fenêtres).",
            "data": None,
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Erreur lors de la prédiction : {e}",
            "data": None,
        }
    finally:
        con.close()
