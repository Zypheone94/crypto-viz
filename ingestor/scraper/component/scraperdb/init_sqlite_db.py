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
    id INTEGER PRIMARY KEY,
    date DATE,
    titre TEXT,
    url TEXT,
    source TEXT,
    symbol TEXT NOT NULL,
    name TEXT,
    price FLOAT,
    market_cap FLOAT,
    coin_circulating FLOAT,
    FOREIGN KEY(symbol) REFERENCES symbol(symbol)
);
''')

con.commit()

print("Tables created :", list(cur.execute("SELECT name FROM sqlite_master WHERE type='table';")))
con.close()
