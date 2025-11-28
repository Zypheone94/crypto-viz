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
            query = """
                SELECT fetched_at, price
                FROM article
                WHERE symbol = %s
                  AND fetched_at >= (UTC_TIMESTAMP() - INTERVAL 1 HOUR)
                ORDER BY fetched_at ASC
            """
        else:
            query = """
                SELECT DATE_FORMAT(fetched_at, '%Y-%m-%d %H:00:00') AS ts,
                       AVG(price) AS price_avg
                FROM article
                WHERE symbol = %s
                  AND fetched_at >= (UTC_TIMESTAMP() - INTERVAL 1 DAY)
                GROUP BY ts
                ORDER BY ts ASC
            """

        cursor.execute(query, (symbol,))
        rows = cursor.fetchall()

        if len(rows) == 0:
            return pd.DataFrame()

        # Build DF
        if timespan == "hour":
            df = pd.DataFrame(rows, columns=["fetched_at", "price"])
            df = df.rename(columns={"fetched_at": "ts"})
        else:
            df = pd.DataFrame(rows, columns=["ts", "price"])
            df["price"] = df["price"].astype(float)

        df["ts"] = pd.to_datetime(df["ts"])
        df = df.set_index("ts")

        df = df[~df.index.duplicated(keep='first')]
        df = df.drop_duplicates(subset=["price"], keep='first')

        if timespan == "hour":
            df = df.resample("1min").mean()

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

    # Pearson
    r = combined.corr().iloc[0, 1]

    print("\n🎯 Pearson correlation:")
    print(f"   r = {r:.4f}")
    print("============================================\n")

    return {
        "symbol1": s1,
        "symbol2": s2,
        "timespan": timespan,
        "usable_points": len(combined),
        "correlation_pearson": round(r, 4),
        "message": "Corrélation calculée avec succès."
    }
