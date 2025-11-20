import math

import mysql.connector
from pathlib import Path
import time
import threading
import pandas as pd
from ingestor.builder.windowed import main as windowed
from ingestor.builder.delta import main as delta

DELTA_TIME = 3600
ARTICLE_TIME = 60

DELTA_PARQUET_DIR = Path("../../../../data/metrics/delta").resolve()
ARTICLE_PARQUET_DIR = Path("../../../../data/clean/parquet").resolve()

"""
window = 1
delta = 1
article = 50
"""

def countdown(get_parquets_function, feed_table_function, duration: int ):
    while True:
        temp_duration = duration
        while temp_duration > 0:
            time.sleep(1)
            temp_duration -= 1
            print(temp_duration)
        df = get_parquets_function()
        feed_table_function(df)

def db_connect():
    try:
        con = mysql.connector.connect(
            host="host.docker.internal",
            user="ingestor_user",
            password="password123",
            database="ingestor")
        print("Connected to database")
        return con
    except mysql.connector.Error as err:
        print("Could not connect to database : ", err)
        return None

def process_feed_article(df: pd.DataFrame) -> None:
    if df is None or df.empty:
        print("Aucun data à traiter")
        return

    df['volume_24h'] = df['volume_24h'].astype(str).str.replace(',', '').str.strip()
    df['coin_circulating'] = df['coin_circulating'].astype(str).str.replace(',', '').str.strip()

    df['volume_24h'] = pd.to_numeric(df['volume_24h'], errors='coerce')
    df['coin_circulating'] = pd.to_numeric(df['coin_circulating'], errors='coerce')

    df = df.dropna(subset=['volume_24h', 'coin_circulating'])

    if df.empty:
        print("Aucun data valide après filtrage des nulls")
        return

    con = db_connect()
    if con is None:
        print("Erreur lors de la connexion à la base de donnée")
        return

    cursor = con.cursor()

    # Récupération des symbols existants
    cursor.execute("SELECT symbol FROM symbol")
    existing_symbols = {row[0] for row in cursor.fetchall()}

    # Récupération des ids déjà présents pour éviter les doublons
    cursor.execute("SELECT id FROM article")
    existing_ids = {row[0] for row in cursor.fetchall()}

    for _, row in df.iterrows():
        data = row.to_dict()

        # Ignorer si symbol inexistant
        if data["symbol"] not in existing_symbols:
            print(f"Symbol {data['symbol']} inexistant, article ignoré")
            continue

        # Ignorer si id déjà existant
        if data["id"] in existing_ids:
            print(f"Article {data['id']} déjà présent, ignoré")
            continue

        # Insertion
        cursor.execute("""
            INSERT INTO article(
                id, fetched_at, url, symbol, name, price, market_cap, volume_24h, coin_circulating
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data["id"],
            data["fetched_at"],
            data["url"],
            data["symbol"],
            data["name"],
            data["price"],
            data["market_cap"],
            data["volume_24h"],
            data["coin_circulating"],
        ))

    con.commit()
    con.close()
    print("Insertion terminée")


def process_feed_delta(df: pd.DataFrame) -> None:
    con = db_connect()
    if con is None:
        print("Impossible de se connecter à la base de données")
        return

    df = df[
        (df["delta"].notna()) &
        (df["delta_pct"].notna()) &
        (df["delta"] != 0) &
        (df["delta_pct"] != 0)
    ]

    if df.empty:
        print("Aucune donnée delta à insérer")
        return

    cursor = con.cursor()

    # Récupérer les symboles existants
    cursor.execute("SELECT symbol FROM symbol")
    existing_symbols = {row[0] for row in cursor.fetchall()}

    # Ignorer les symboles inexistants pour éviter l'erreur de clé étrangère
    df = df[df["symbol"].isin(existing_symbols)]

    for _, row in df.iterrows():
        cursor.execute("""
            INSERT INTO delta(symbol, date_start, date_end, window_label, delta, delta_pct)
            VALUES(%s, %s, %s, %s, %s, %s)
        """, (
            row["symbol"],
            str(row["window_start"]),
            str(row["window_end"]),
            "1h",
            row["delta"],
            row["delta_pct"]
        ))

    con.commit()
    con.close()

def delta_feeder() -> None:
    windowed()
    delta()

def get_parquets(parquet_path: Path, type) -> pd.DataFrame | None:
    dataframes = []
    if type == "delta":
        delta_feeder()
    try:
        for file in parquet_path.rglob("*.parquet"):
            if file.is_file():
                print(file)
                df = pd.read_parquet(file)
                dataframes.append(df)
                if type == "article":
                    file.unlink()
        if dataframes:
            content = pd.concat(dataframes, ignore_index=True)
            return content
        else:
            print("No parquet files found")
            return None
    except Exception as exc:
        print("Failed to read %s: %s", parquet_path, exc)
        return None


def main() -> None:
    thread_articles = threading.Thread(target=countdown, args=(lambda: get_parquets(ARTICLE_PARQUET_DIR, "article"), process_feed_article, ARTICLE_TIME))
    thread_delta = threading.Thread(target=countdown, args=(lambda: get_parquets(DELTA_PARQUET_DIR, "delta"), process_feed_delta, DELTA_TIME))

    thread_articles.start()
    thread_delta.start()

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
