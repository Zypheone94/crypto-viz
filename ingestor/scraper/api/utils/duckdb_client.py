"""DuckDB helper utilities for the metrics API.

This module maintains a DuckDB warehouse (`warehouse.duckdb`) populated from the
clean Parquet lake. Queries exposed by the API always read from the warehouse so
the schema defined in `scrapper/scrapperdb/duck_schema.py` is fully leveraged.
"""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import date, datetime
from glob import glob
from pathlib import Path
from typing import Iterable, Literal

import duckdb
from ingestor.scraper.component.scrapperdb.duck_schema import apply_schema

from  scraper.component.scrapperdb.duck_schema import ensure_physical_tables


logger = logging.getLogger(__name__)

PARQUET_GLOB_ENV = "CRYPTO_VIZ_PARQUET_GLOB"
WAREHOUSE_DB_ENV = "CRYPTO_VIZ_WAREHOUSE_DB"
BASE_DIR_ENV = "CRYPTO_VIZ_BASE_DIR"

_WAREHOUSE_SIGNATURE: str | None = None

def _default_base_dir() -> Path:
    return Path(__file__).resolve().parents[3]

def _resolve_base_dir() -> Path:
    """
    Retourne le répertoire racine des données.
    - Priorité à la variable d'env BASE_DIR_ENV
    - Sinon, détecte automatiquement Docker / conteneur
    - Sinon fallback sur le parent de __file__.
    """
    override = os.getenv(BASE_DIR_ENV)
    if override:
        return Path(override)

    # Si on est dans Docker, on est souvent sous /app/ingestor
    docker_path = Path("/app/ingestor")
    if docker_path.exists():
        return docker_path  # ✅ Retourne /app/ingestor

    # Fallback classique
    return Path(__file__).resolve().parents[3]

def get_parquet_glob_pattern() -> str:
    override = os.getenv(PARQUET_GLOB_ENV)
    if override:
        return override
    base_dir = _resolve_base_dir()
    return str(base_dir / "data" / "clean" / "parquet" / "**" / "*.parquet")

def get_warehouse_path() -> Path:
    override = os.getenv(WAREHOUSE_DB_ENV)
    if override:
        return Path(override)
    base_dir = _resolve_base_dir()
    return base_dir / "scraper" / "data" / "duck" / "warehouse.duckdb"

def _build_files_signature(files: list[str]) -> str | None:
    if not files:
        return None
    digest = hashlib.sha1()
    for path in sorted(files):
        try:
            stat = os.stat(path)
        except FileNotFoundError:
            continue
        digest.update(path.encode("utf-8"))
        digest.update(str(stat.st_mtime_ns).encode("utf-8"))
        digest.update(str(stat.st_size).encode("utf-8"))
    return digest.hexdigest()

def _format_bucket(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time()).isoformat()
    return str(value)

def _format_file_array(files: Iterable[str]) -> str:
    """Retourne une chaîne SQL compatible DuckDB pour read_parquet(['f1','f2',...])"""
    # DuckDB attend un tableau, pas des arguments séparés
    files_list = [f"'{str(Path(path).resolve())}'" for path in files]
    return "[" + ", ".join(files_list) + "]"

def _refresh_warehouse(files: list[str]) -> None:
    warehouse_path = get_warehouse_path()
    warehouse_path.parent.mkdir(parents=True, exist_ok=True)

    file_array_sql = _format_file_array(files)

    with duckdb.connect(str(warehouse_path)) as con:
        ensure_physical_tables(con)

        # Reset tables
        for table in ["metrics_trending", "metrics_sources_daily", "metrics_delta",
                      "metrics_windowed", "latest", "articles"]:
            con.execute(f"DELETE FROM {table}")

        if files:
            logger.info("Chargement de %d fichiers Parquet dans DuckDB", len(files))
            con.execute(
                f"""
                INSERT INTO articles
                WITH raw AS (
                    SELECT
                        id,
                        CAST(ts AS TIMESTAMP) AS ts,
                        COALESCE(date, CAST(ts AS DATE)) AS date,
                        title,
                        url,
                        source,
                        TRY_CAST(fetched_at AS TIMESTAMP) AS fetched_at
                    FROM read_parquet({file_array_sql})
                ), dedup AS (
                    SELECT *
                    FROM raw
                    QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY ts DESC) = 1
                )
                SELECT * FROM dedup
                """
            )

            # Windowed metrics
            con.execute(
                """
                INSERT INTO metrics_windowed
                SELECT
                    window_start,
                    window_start + INTERVAL 1 DAY AS window_end,
                    COUNT(*) AS count
                FROM (
                    SELECT date_trunc('day', ts) AS window_start FROM articles
                )
                GROUP BY window_start
                ORDER BY window_start
                """
            )

            # Daily deltas
            con.execute(
                """
                INSERT INTO metrics_delta
                WITH daily AS (
                    SELECT date, COUNT(*) AS count
                    FROM articles
                    GROUP BY date
                ), ranked AS (
                    SELECT date, count,
                           LAG(count) OVER (ORDER BY date) AS prev_count
                    FROM daily
                )
                SELECT date, count,
                       count - COALESCE(prev_count, 0) AS delta_abs,
                       CASE
                           WHEN prev_count IS NULL OR prev_count = 0 THEN NULL
                           ELSE CAST((count - prev_count) AS DOUBLE) / prev_count * 100.0
                       END AS delta_pct
                FROM ranked
                ORDER BY date
                """
            )

            # Daily volume by source
            con.execute(
                """
                INSERT INTO metrics_sources_daily
                SELECT date, source, COUNT(*) AS count
                FROM articles
                GROUP BY date, source
                ORDER BY date, source
                """
            )

            # Trending (top 10)
            con.execute(
                """
                INSERT INTO metrics_trending
                WITH ranked AS (
                    SELECT date_trunc('day', ts) AS ts_window_start,
                           source AS keyword,
                           COUNT(*) AS count,
                           ROW_NUMBER() OVER (
                               PARTITION BY date_trunc('day', ts)
                               ORDER BY COUNT(*) DESC, source
                           ) AS rn
                    FROM articles
                    GROUP BY 1, 2
                )
                SELECT ts_window_start, keyword, count
                FROM ranked
                WHERE rn <= 10
                ORDER BY ts_window_start, keyword
                """
            )

            # Snapshot
            con.execute(
                """
                INSERT INTO latest(metric, count, updated_at)
                SELECT metric, count, updated_at
                FROM (
                    SELECT source AS metric,
                           COUNT(*) AS count,
                           MAX(ts) AS updated_at
                    FROM articles
                    GROUP BY source
                    UNION ALL
                    SELECT 'total' AS metric,
                           COUNT(*) AS count,
                           MAX(ts) AS updated_at
                    FROM articles
                )
                """
            )

            # Debug simple
            print("\n=== Debug insertions ===")
            for table in ["articles", "metrics_windowed", "metrics_delta",
                          "metrics_sources_daily", "metrics_trending", "latest"]:
                cnt = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                print(f"{table}: {cnt} lignes insérées")

        logger.info("DuckDB warehouse refreshed at %s", warehouse_path)

def _ensure_warehouse_loaded(force: bool = False) -> None:
    global _WAREHOUSE_SIGNATURE
    pattern = get_parquet_glob_pattern()
    files = glob(pattern, recursive=True)
    signature = _build_files_signature(files)

    if force or signature != _WAREHOUSE_SIGNATURE:
        _refresh_warehouse(files)
        _WAREHOUSE_SIGNATURE = signature

def query_timeseries(dt_from: datetime, dt_to: datetime, bucket: Literal["hour", "day"]) -> list[dict[str, object]]:
    _ensure_warehouse_loaded()
    warehouse_path = get_warehouse_path()
    with duckdb.connect(str(warehouse_path)) as con:
        rows = con.execute(
            f"""
            SELECT date_trunc('{bucket}', ts) AS bucket_start, COUNT(*) AS value
            FROM articles
            WHERE ts >= ? AND ts <= ?
            GROUP BY bucket_start
            ORDER BY bucket_start
            """, [dt_from, dt_to]
        ).fetchall()
    return [{"t": _format_bucket(bucket_start), "value": value} for bucket_start, value in rows]

def read_latest_snapshot() -> dict[str, object]:
    _ensure_warehouse_loaded()
    warehouse_path = get_warehouse_path()
    with duckdb.connect(str(warehouse_path)) as con:
        rows = con.execute("SELECT metric, count, updated_at FROM latest").fetchall()
    if not rows:
        return {"updated_at": None, "counts": {}}
    counts = {metric: count for metric, count, _ in rows}
    latest_ts = max((row[2] for row in rows if row[2] is not None), default=None)
    return {"updated_at": latest_ts.isoformat() if isinstance(latest_ts, datetime) else None, "counts": counts}

def refresh_warehouse(force: bool = False) -> None:
    """Public helper to force a warehouse refresh."""
    _ensure_warehouse_loaded(force=force)
