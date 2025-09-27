"""Schéma DuckDB minimal : création des 5 tables demandées.

Tables :
 1. articles
 2. metrics_windowed
 3. metrics_delta
 4. metrics_sources_daily
 5. metrics_trending

Aucune logique de calcul ici : uniquement le DDL.
"""
from __future__ import annotations
import os, pathlib, duckdb

DUCKDB_FILE = pathlib.Path(os.getenv("DUCKDB_FILE", "../data/duck/warehouse.duckdb"))
DUCKDB_FILE.parent.mkdir(parents=True, exist_ok=True)

DDL = [
    """
    CREATE TABLE IF NOT EXISTS articles (
        id VARCHAR PRIMARY KEY,
        ts TIMESTAMP,          -- publication UTC
        date DATE,             -- dérivé de ts
        title VARCHAR,
        url VARCHAR,
        source VARCHAR,
        fetched_at TIMESTAMP   -- récupération
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS metrics_windowed (
        window_start TIMESTAMP,
        window_end TIMESTAMP,
        count BIGINT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS metrics_delta (
        date DATE PRIMARY KEY,
        count BIGINT,
        delta_abs BIGINT,
        delta_pct DOUBLE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS metrics_sources_daily (
        date DATE,
        source VARCHAR,
        count BIGINT,
        PRIMARY KEY(date, source)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS metrics_trending (
        ts_window_start TIMESTAMP,
        keyword VARCHAR,
        count BIGINT
    )
    """,
    # Index simples pour requêtes fréquentes
    "CREATE INDEX IF NOT EXISTS idx_articles_date ON articles(date)",
    "CREATE INDEX IF NOT EXISTS idx_articles_ts ON articles(ts)",
]

def init_schema():
    con = duckdb.connect(str(DUCKDB_FILE))
    for stmt in DDL:
        con.execute(stmt)
    con.close()

if __name__ == "__main__":
    init_schema()
    print(f"Schéma DuckDB créé dans {DUCKDB_FILE}")
