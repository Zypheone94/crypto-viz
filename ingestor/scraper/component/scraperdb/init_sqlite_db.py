import sqlite3
from pathlib import Path
import os

data_dir = Path(__file__).parent / "data"
data_dir.mkdir(exist_ok=True)
con = sqlite3.connect(str(data_dir / "ingestor.db"))
cur = con.cursor()

cur.execute('''
CREATE TABLE IF NOT EXISTS symbol (
    id INTEGER PRIMARY KEY,
    symbol TEXT UNIQUE NOT NULL
);
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS delta (
    id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    date_start TIMESTAMP,
    date_end DATE,
    window_label TEXT,
    delta FLOAT,
    delta_pct FLOAT,
    FOREIGN KEY(symbol) REFERENCES symbol(symbol)
);
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS article (
    id TEXT PRIMARY KEY,
    fetched_at TIMESTAMP,
    url TEXT,
    symbol TEXT NOT NULL,
    name TEXT,
    price FLOAT,
    market_cap FLOAT,
    volume_24h FLOAT,
    coin_circulating FLOAT,
    FOREIGN KEY(symbol) REFERENCES symbol(symbol)
);
''')

cur.execute('''
        CREATE OR REPLACE VIEW ml_features AS
        SELECT
            d.symbol,
            d.date_start,
            d.date_end,
            d.delta_pct AS target_delta_pct,
            CASE WHEN d.delta_pct > 0 THEN 1 ELSE 0 END AS target_up,
            COUNT(a.id)                     AS nb_articles,
            AVG(a.price)                    AS avg_price,
            AVG(a.market_cap)               AS avg_market_cap,
            AVG(a.coin_circulating)         AS avg_circulating
        FROM delta d
        LEFT JOIN article a
            ON a.symbol = d.symbol
         AND a.fetched_at >= d.date_start
         AND a.fetched_at <  d.date_end
        GROUP BY 1,2,3,4,5;
''')

con.commit()

print("Tables created :", list(cur.execute("SELECT name FROM sqlite_master WHERE type='table';")))
con.close()
