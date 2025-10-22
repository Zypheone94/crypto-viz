"""DuckDB helper utilities for the metrics API.

This module maintains a DuckDB warehouse (`warehouse.duckdb`) populated from the
clean Parquet lake. Queries exposed by the API always read from the warehouse so
the schema defined in `scrapper/scrapperdb/duck_schema.py` is fully leveraged.
"""

# Code ajouté par Alexandru : orchestration du chargement du warehouse DuckDB.

from __future__ import annotations

import hashlib
import logging
import os
from datetime import date, datetime
from glob import glob
from pathlib import Path
from typing import Iterable, Literal

import duckdb

from  scraper.component.scrapperdb.duck_schema import ensure_physical_tables, rebuild_from_parquet


logger = logging.getLogger(__name__)


PARQUET_GLOB_ENV = "CRYPTO_VIZ_PARQUET_GLOB"
WAREHOUSE_DB_ENV = "CRYPTO_VIZ_WAREHOUSE_DB"
BASE_DIR_ENV = "CRYPTO_VIZ_BASE_DIR"


_WAREHOUSE_SIGNATURE: str | None = None


def _default_base_dir() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve_base_dir() -> Path:
    override = os.getenv(BASE_DIR_ENV)
    return Path(override) if override else _default_base_dir()


def get_parquet_glob_pattern() -> str:
    override = os.getenv(PARQUET_GLOB_ENV)
    if override:
        return override
    base_dir = _resolve_base_dir()
    repo_root = base_dir.parent

    candidates = [
        base_dir / "data" / "clean" / "parquet" / "**" / "*.parquet",
        repo_root / "data" / "clean" / "parquet" / "**" / "*.parquet",
    ]

    for path in candidates:
        matches = glob(str(path), recursive=True)
        if matches:
            return str(path)

    # Fallback to metrics materialisations (ingestor or repo root)
    metric_candidates = [
        base_dir / "data" / "metrics" / "**" / "*.parquet",
        repo_root / "data" / "metrics" / "**" / "*.parquet",
    ]

    for path in metric_candidates:
        matches = glob(str(path), recursive=True)
        if matches:
            return str(path)

    # Default to first clean path so caller still gets a sensible value
    return str(candidates[0])


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
    escaped = [
        f"'{str(Path(path).resolve()).replace("'", "''")}'" for path in files
    ]
    return f"[{', '.join(escaped)}]"


def _refresh_warehouse(files: list[str]) -> None:
    warehouse_path = get_warehouse_path()
    warehouse_path.parent.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(warehouse_path)) as con:
        rebuild_from_parquet(con, files)
        
    logger.info("DuckDB warehouse refreshed at %s", warehouse_path)


def _ensure_warehouse_loaded(force: bool = False) -> None:
    global _WAREHOUSE_SIGNATURE

    pattern = get_parquet_glob_pattern()
    files = glob(pattern, recursive=True)
    signature = _build_files_signature(files)

    if force or signature != _WAREHOUSE_SIGNATURE:
        _refresh_warehouse(files)
        _WAREHOUSE_SIGNATURE = signature


def query_timeseries(
    dt_from: datetime,
    dt_to: datetime,
    bucket: Literal["hour", "day"],
) -> list[dict[str, object]]:
    _ensure_warehouse_loaded()
    warehouse_path = get_warehouse_path()

    with duckdb.connect(str(warehouse_path)) as con:
        rows = con.execute(
            f"""
            SELECT
                date_trunc('{bucket}', ts) AS bucket_start,
                COUNT(*) AS value
            FROM articles
            WHERE ts >= ? AND ts <= ?
            GROUP BY bucket_start
            ORDER BY bucket_start
            """,
            [dt_from, dt_to],
        ).fetchall()

    return [{"t": _format_bucket(bucket_start), "value": value} for bucket_start, value in rows]


def read_latest_snapshot() -> dict[str, object]:
    _ensure_warehouse_loaded()
    warehouse_path = get_warehouse_path()

    with duckdb.connect(str(warehouse_path)) as con:
        rows = con.execute(
            "SELECT metric, count, updated_at FROM latest"
        ).fetchall()

    if not rows:
        return {"updated_at": None, "counts": {}}

    counts = {metric: count for metric, count, _ in rows}
    updated_at_values: Iterable[datetime | None] = (row[2] for row in rows)
    latest_ts = max((ts for ts in updated_at_values if ts is not None), default=None)

    return {
        "updated_at": latest_ts.isoformat() if isinstance(latest_ts, datetime) else None,
        "counts": counts,
    }


def refresh_warehouse(force: bool = False) -> None:
    """Public helper to force a warehouse refresh (e.g., from a CLI)."""

    _ensure_warehouse_loaded(force=force)