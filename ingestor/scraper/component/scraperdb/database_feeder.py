"""Automated feeder that pulls cleaned parquet files into the SQLite warehouse."""

from __future__ import annotations

import logging
import os
import shutil
import sqlite3
import time
from pathlib import Path
from typing import Iterable

import pandas as pd
from dotenv import load_dotenv

from ingestor.builder.windowed import main as windowed_main
from ingestor.builder.delta import main as delta_main


LOGGER = logging.getLogger("database_feeder")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parents[3] / ".env")


def _resolve(path: Path) -> Path:
    if path.is_absolute():
        return path
    return (Path.cwd() / path).resolve()


OUT_DIR = _resolve(Path(os.getenv("OUT_DIR", "../data/clean/parquet")))
DELTA_PARQUET_DIR = _resolve(Path("../data/metrics/delta"))
REJECT_DIR = OUT_DIR.parent / "_corrupt"
RETAIN_DIR = OUT_DIR.parent / "_retained"
RETAIN_MAX = int(os.getenv("FEEDER_RETAIN_FILES", "5"))
DB_PATH = _resolve(Path(os.getenv("FEEDER_DB_PATH", "ingestor/scraper/component/scraperdb/data/ingestor.db")))
POLL_SECONDS = int(os.getenv("FEEDER_POLL_SECONDS", "60"))
RETAIN_MAX = max(RETAIN_MAX, 0)


def find_parquet_files(base_dir: Path) -> list[Path]:
    if not base_dir.exists():
        LOGGER.warning("OUT_DIR does not exist: %s", base_dir)
        return []
    return sorted(p for p in base_dir.rglob("*.parquet") if p.is_file())


def load_frame(path: Path) -> pd.DataFrame | None:
    try:
        return pd.read_parquet(path)
    except Exception as exc:  # pragma: no cover - safety net
        LOGGER.error("Failed to read %s: %s", path, exc)
        return None


def normalise_frame(df: pd.DataFrame) -> pd.DataFrame:
    renamed = df.rename(columns={c: c.lower() for c in df.columns})
    aliases = {
        "headline": "titre",
        "link": "url",
        "price_usd": "price",
        "market_cap_usd": "market_cap",
        "marketcap": "market_cap",
        "marketCap": "market_cap",
        "circulating_supply": "coin_circulating",
        "circulating": "coin_circulating",
        "date": "fetched_at",
    }
    for original, alias in aliases.items():
        if original in renamed.columns and alias not in renamed.columns:
            renamed = renamed.rename(columns={original: alias})

    expected = [
        "fetched_at",
        "url",
        "symbol",
        "name",
        "price",
        "market_cap",
        "coin_circulating",
    ]
    for col in expected:
        if col not in renamed.columns:
            renamed[col] = None

    numeric_cols = ["price", "market_cap", "coin_circulating"]
    for col in numeric_cols:
        renamed[col] = pd.to_numeric(renamed[col], errors="coerce")

    return renamed[expected]


def ensure_reject_dir() -> None:
    if not REJECT_DIR.exists():
        REJECT_DIR.mkdir(parents=True, exist_ok=True)


def move_to_reject(path: Path) -> None:
    ensure_reject_dir()
    target = REJECT_DIR / path.name
    LOGGER.warning("Moving %s to %s", path, target)
    shutil.move(str(path), target)


def clean_parent_dirs(path: Path) -> None:
    parent = path.parent
    try:
        parent.rmdir()
    except OSError:
        return
    # Avoid removing the OUT_DIR itself; only prune empty date folders.
    grandparent = parent.parent
    if grandparent.exists() and grandparent != OUT_DIR:
        try:
            grandparent.rmdir()
        except OSError:
            pass


def clean_retained_dirs(path: Path) -> None:
    parent = path.parent
    try:
        parent.rmdir()
    except OSError:
        return
    grandparent = parent.parent
    if grandparent.exists() and grandparent != RETAIN_DIR:
        try:
            grandparent.rmdir()
        except OSError:
            pass


def prune_retained() -> None:
    if RETAIN_MAX <= 0 or not RETAIN_DIR.exists():
        return
    files = sorted(
        (p for p in RETAIN_DIR.rglob("*.parquet") if p.is_file()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for stale in files[RETAIN_MAX:]:
        stale.unlink(missing_ok=True)
        clean_retained_dirs(stale)


def retain_file(src: Path) -> None:
    if RETAIN_MAX <= 0:
        src.unlink(missing_ok=True)
        clean_parent_dirs(src)
        return

    relative = src.relative_to(OUT_DIR)
    dest = RETAIN_DIR / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), dest)
    prune_retained()
    clean_parent_dirs(src)


def ingest_rows(cur: sqlite3.Cursor, rows: Iterable[dict]) -> tuple[int, int]:
    inserted = 0
    for row in rows:
        symbol = row.get("symbol")

        if symbol:
            cur.execute("INSERT OR IGNORE INTO symbol(symbol) VALUES (?)", (symbol,))

        cur.execute(
            """
            INSERT INTO article(fetched_at, url, symbol, name, price, market_cap, coin_circulating)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.get("fetched_at"),
                row.get("url"),
                symbol,
                row.get("name"),
                row.get("price"),
                row.get("market_cap"),
                row.get("coin_circulating"),
            ),
        )

        inserted += 1

    return inserted, 0


def process_file(cur: sqlite3.Cursor, path: Path, process_func) -> tuple[int, int]:
    frame = load_frame(path)
    if frame is None:
        move_to_reject(path)
        return 0, 0

    if frame.empty:
        LOGGER.info("Skipping empty parquet %s", path)
        path.unlink(missing_ok=True)
        clean_parent_dirs(path)
        return 0, 0

    payload = normalise_frame(frame)
    result = process_func(payload)
    LOGGER.info("File %s: inserted=%s skipped=%s", path, result[0], result[1])

    retain_file(path)

    return result


def run_cycle() -> None:
    files = find_parquet_files(OUT_DIR)
    if not files:
        LOGGER.info("No parquet files found under %s", OUT_DIR)
        return

    LOGGER.info("Processing %s file(s) from %s", len(files), OUT_DIR)

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    try:
        cur = con.cursor()
        inserted_total = 0
        skipped_total = 0

        def process_with_ingest(payload: pd.DataFrame) -> tuple[int, int]:
            return ingest_rows(cur, payload.to_dict("records"))

        for file_path in files:
            inserted, skipped = process_file(cur, file_path, process_with_ingest)
            inserted_total += inserted
            inserted_total += inserted
            skipped_total += skipped

        con.commit()
        LOGGER.info("Cycle stats: inserted=%s skipped=%s", inserted_total, skipped_total)
    finally:
        con.close()

def populate_delta_parquets() -> None:
    windowed_main()
    delta_main()
    populate_delta_table()

"""def feed_delta_table() -> None:
    for row in rows:
"""

def populate_delta_table() -> None:
    files = find_parquet_files(DELTA_PARQUET_DIR)
    if not files:
        LOGGER.info("No parquet files found under %s", OUT_DIR)
        return

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    try:
        cur = con.cursor()
    except:
        LOGGER.info("No database found under %s", OUT_DIR)
        return

def main() -> None:
    LOGGER.info(
        "Feeder starting with OUT_DIR=%s DB=%s interval=%ss",
        OUT_DIR, DB_PATH, POLL_SECONDS
    )
    hour_countdown = 0
    try:
        while True:
            start = time.time()
            run_cycle()
            duration = int(time.time() - start)
            hour_countdown += duration

            for _ in range(POLL_SECONDS):
                time.sleep(1)
                hour_countdown += 1

                if hour_countdown >= 15:
                    print("delta parquets ready")
                    populate_delta_parquets()
                    hour_countdown = 0

    except KeyboardInterrupt:
        LOGGER.info("Shutdown requested")


if __name__ == "__main__":
    main()