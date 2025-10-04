"""Initialisation du schéma DuckDB partagé.

Tables créées :
1. ``articles``
2. ``metrics_windowed``
3. ``metrics_delta``
4. ``metrics_sources_daily``
5. ``metrics_trending``
6. ``latest`` (ajouté pour les snapshots de métriques)

Ce module ne charge pas les données : il définit uniquement la structure. Il est
réutilisé côté API pour garantir une source de vérité unique.
"""

from __future__ import annotations

import os
import pathlib
from typing import Iterable

import duckdb

# Code ajouté par Alexandru : schéma centralisé pour le warehouse DuckDB.

DUCKDB_FILE = pathlib.Path(os.getenv("DUCKDB_FILE", "../data/duck/warehouse.duckdb"))
DUCKDB_FILE.parent.mkdir(parents=True, exist_ok=True)

DDL = (
    """
    CREATE TABLE IF NOT EXISTS articles (
        id VARCHAR PRIMARY KEY,
        ts TIMESTAMP,
        date DATE,
        title VARCHAR,
        url VARCHAR,
        source VARCHAR,
        fetched_at TIMESTAMP
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
    """
    CREATE TABLE IF NOT EXISTS latest (
        metric VARCHAR PRIMARY KEY,
        count BIGINT,
        updated_at TIMESTAMP
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_articles_date ON articles(date)",
    "CREATE INDEX IF NOT EXISTS idx_articles_ts ON articles(ts)",
)


def apply_schema(connection: duckdb.DuckDBPyConnection, statements: Iterable[str] | None = None) -> None:
    """Applique les instructions DDL fournies (ou celles par défaut)."""

    for stmt in statements or DDL:
        connection.execute(stmt)


def init_schema(db_path: pathlib.Path | None = None) -> None:
    """Initialise le fichier DuckDB cible en créant toutes les tables."""

    target = pathlib.Path(db_path or DUCKDB_FILE)
    target.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(target))
    try:
        apply_schema(connection)
    finally:
        connection.close()


if __name__ == "__main__":
    init_schema()
    print(f"Schéma DuckDB créé dans {DUCKDB_FILE}")
