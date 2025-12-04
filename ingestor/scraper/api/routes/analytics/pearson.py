import pandas as pd
import mysql.connector
from fastapi import APIRouter, HTTPException
from typing import Literal

router = APIRouter()


def db_connect():
    try:
        con = mysql.connector.connect(
            host="host.docker.internal",
            user="ingestor_user",
            password="password123",
            database="ingestor"
        )
        return con
    except mysql.connector.Error as err:
        return None


def fetch_data_from_db(con, symbol: str, timespan: str) -> pd.DataFrame:
    cursor = con.cursor(buffered=True)

    try:
        if timespan == "hour":
            # Pour timespan="hour" : données par minute sur la dernière heure
            query = """
                    SELECT DATE_FORMAT(fetched_at, '%Y-%m-%d %H:%i:00') AS ts,
                           AVG(price) AS price_avg
                    FROM article
                    WHERE symbol = %s
                      AND fetched_at >= (UTC_TIMESTAMP() - INTERVAL 1 HOUR)
                    GROUP BY ts
                    ORDER BY ts ASC
                    """
        else:
            # Pour timespan="day" : données par heure sur les dernières 24 heures
            query = """
                    SELECT DATE_FORMAT(fetched_at, '%Y-%m-%d %H:00:00') AS ts,
                           AVG(price) AS price_avg
                    FROM article
                    WHERE symbol = %s
                      AND fetched_at >= (UTC_TIMESTAMP() - INTERVAL 24 HOUR)
                    GROUP BY ts
                    ORDER BY ts ASC
                    """

        print(f"🔍 Exécution de la requête pour {symbol}:")
        print(f"SQL: {query}")
        cursor.execute(query, (symbol,))
        rows = cursor.fetchall()

        if len(rows) == 0:
            print(f"❌ Aucune donnée trouvée pour {symbol}")
            return pd.DataFrame()
        
        print(f"✅ {len(rows)} lignes trouvées pour {symbol}")
        if len(rows) > 0:
            print(f"Premier timestamp: {rows[0][0]}")
            print(f"Dernier timestamp: {rows[-1][0]}")

        # Build DF - maintenant les deux cas utilisent la même structure
        df = pd.DataFrame(rows, columns=["ts", "price"])
        df["price"] = df["price"].astype(float)

        df["ts"] = pd.to_datetime(df["ts"])
        df = df.set_index("ts")

        df = df[~df.index.duplicated(keep='first')]
        df = df.drop_duplicates(subset=["price"], keep='first')

        # Plus besoin de resampling car les données sont déjà agrégées dans la requête SQL

        return df.dropna()

    finally:
        cursor.close()


@router.get("/correlation", tags=["data-analysis"])
async def get_correlation(
        symbol1: str,
        symbol2: str,
        timespan: Literal["hour", "day"] = "hour"
):
    print("\n============================================")
    print(f"📡 Correlation request: {symbol1} vs {symbol2} ({timespan})")
    if timespan == "hour":
        print("⏰ Mode: Données par minute sur la dernière heure")
    else:
        print("📅 Mode: Données par heure sur les dernières 24 heures")
    print("============================================")

    con = db_connect()
    if not con:
        raise HTTPException(status_code=503, detail="Impossible de se connecter à MySQL.")

    try:
        s1, s2 = symbol1.upper(), symbol2.upper()

        df1 = fetch_data_from_db(con, s1, timespan)
        df2 = fetch_data_from_db(con, s2, timespan)

    finally:
        con.close()

    if df1.empty or df2.empty:
        raise HTTPException(status_code=404, detail="Pas assez de données après filtrage.")

    # rename columns
    df1 = df1.rename(columns={"price": f"price_{s1}"})
    df2 = df2.rename(columns={"price": f"price_{s2}"})

    combined = df1.join(df2, how="inner").dropna()

    if len(combined) < 3:
        raise HTTPException(status_code=400, detail="Moins de 3 points utilisables.")

    # Debug limited view
    print("\n📊 VALUES USED FOR PEARSON (first 10)")
    print(combined.head(10))
    print(f"\nTotal aligned points: {len(combined)}")
    
    # Debug des timestamps pour voir les vraies dates
    print(f"\n📅 TIMESTAMPS DEBUG:")
    print(f"Premier timestamp: {combined.index[0]}")
    print(f"Dernier timestamp: {combined.index[-1]}")
    print(f"Type des index: {type(combined.index[0])}")

    # Pearson
    r = combined.corr().iloc[0, 1]

    print("\n🎯 Pearson correlation:")
    print(f"   r = {r:.4f}")
    print("============================================\n")

    # Préparer les données pour le plot
    combined_reset = combined.reset_index()
    
    # Garder les timestamps au format ISO pour le parsing du frontend
    iso_timestamps = combined_reset["ts"].dt.strftime("%Y-%m-%d %H:%M:%S").tolist()
    
    # Format d'affichage selon l'intervalle
    if timespan == "hour":
        # Pour les minutes : afficher DD/MM/YYYY HH:MM
        display_format = "%d/%m/%Y %H:%M"
    else:
        # Pour les heures : toujours afficher DD/MM/YYYY HH:00
        display_format = "%d/%m/%Y %H:00"
    
    display_timestamps = combined_reset["ts"].dt.strftime(display_format).tolist()
    
    # Debug des timestamps
    print(f"\n🕐 TIMESTAMPS DEBUG ({timespan}):")
    print(f"Premier ISO: {iso_timestamps[0] if iso_timestamps else 'None'}")
    print(f"Premier Display: {display_timestamps[0] if display_timestamps else 'None'}")
    print(f"Dernier ISO: {iso_timestamps[-1] if iso_timestamps else 'None'}")
    print(f"Dernier Display: {display_timestamps[-1] if display_timestamps else 'None'}")
    print(f"Total: {len(iso_timestamps)}")

    plot_data = {
        "timestamps": iso_timestamps,
        "display_timestamps": display_timestamps,
        "series": [
            {
                "name": s1,
                "data": combined_reset[f"price_{s1}"].round(4).tolist(),
                "color": "#3b82f6"  # blue
            },
            {
                "name": s2,
                "data": combined_reset[f"price_{s2}"].round(4).tolist(),
                "color": "#ef4444"  # red
            }
        ]
    }

    return {
        "symbol1": s1,
        "symbol2": s2,
        "timespan": timespan,
        "usable_points": len(combined),
        "correlation_pearson": round(r, 4),
        "plot_data": plot_data,
        "statistics": {
            f"{s1}_mean": round(combined[f"price_{s1}"].mean(), 4),
            f"{s1}_std": round(combined[f"price_{s1}"].std(), 4),
            f"{s2}_mean": round(combined[f"price_{s2}"].mean(), 4),
            f"{s2}_std": round(combined[f"price_{s2}"].std(), 4),
        },
        "message": "Corrélation calculée avec succès."
    }