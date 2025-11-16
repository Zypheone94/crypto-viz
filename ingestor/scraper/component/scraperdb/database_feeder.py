import sqlite3
from pathlib import Path
from typing import Iterable
import time
import threading
import pandas as pd

DELTA_TIME = 15
ARTICLE_TIME = 60

DB_PATH = Path("ingestor/scraper/component/scraperdb/data/ingestor.db")
DELTA_PARQUET_DIR = Path("../../../../data/metrics/delta")
ARTICLE_PARQUET_DIR = Path("../../../../data/clean/parquet").resolve()

"""
window = 1
delta = 1
article = 50
"""

def countdown(get_parquets_function, feed_table_function, duration: int):
    while True:
        temp_duration = duration
        while temp_duration > 0:
            time.sleep(1)
            temp_duration -= 1
            print(temp_duration)
        df = get_parquets_function()
        feed_table_function(df)

def db_connect(db_path: Path):
    print(db_path)
    try:
        con = sqlite3.connect(db_path)
        return con
    except sqlite3.OperationalError:
        print("Could not connect to database")
        return None

def process_feed_article(df: pd.DataFrame) -> None:
    con = db_connect(DB_PATH.absolute())
    if con is None:
        print("Erreur lors de la connexion à la base de donnée")
        return
    cursor = con.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"📋 Tables disponibles : {tables}")

    for i, row in df.iterrows():
        cursor.execute("SELECT 1 FROM article WHERE id = ?", (row["id"],))

        if cursor.fetchone() is not None:
            continue

        cursor.execute("""
        INSERT INTO article(id, fetched_at, url, symbol, name, price, market_cap, volume_24h, coin_circulating)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                       (row["id"], row["fetched_at"], row["url"], row["symbol"], row["name"], row["price"], row["market_cap"], row["volume_24h"], row["coin_circulating"]))
        con.commit()
    con.close()


def get_parquets(parquet_path: Path) -> pd.DataFrame | None:
    dataframes = []
    try:
        for file in parquet_path.rglob("*.parquet"):
            if file.is_file():
                df = pd.read_parquet(file)
                dataframes.append(df)
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
    print(DB_PATH.absolute())

    thread_articles = threading.Thread(target=countdown, args=(lambda: get_parquets(ARTICLE_PARQUET_DIR), process_feed_article, ARTICLE_TIME))
    #thread_delta = threading.Thread(target=countdown, args=(get_delta_parquets, DELTA_TIME))

    thread_articles.start()
    #thread_delta.start()

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
