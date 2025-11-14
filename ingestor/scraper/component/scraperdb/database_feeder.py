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


LOGGER = logging.getLogger("database_feeder")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parents[3] / ".env")


def _resolve(path: Path) -> Path:
    if path.is_absolute():
        return path
    return (Path.cwd() / path).resolve()


OUT_DIR = _resolve(Path(os.getenv("OUT_DIR", "../data/clean/parquet")))
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
        "title": "titre",
        "headline": "titre",
        "link": "url",
        "source_name": "source",
        "marketcap": "market_cap",
        "marketCap": "market_cap",
        "circulating_supply": "coin_circulating",
        "circulating": "coin_circulating",
    }
    for original, alias in aliases.items():
        if original in renamed.columns and alias not in renamed.columns:
            renamed = renamed.rename(columns={original: alias})

    expected = [
        "date",
        "titre",
        "url",
        "source",
        "symbol",
        "name",
        "price",
        "market_cap",
        "coin_circulating",
    ]
    for col in expected:
        if col not in renamed.columns:
            renamed[col] = None

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
    # Attempt to clean one level up if the date folder became empty.
    try:
        parent.parent.rmdir()
    except OSError:
        pass


def clean_retained_dirs(path: Path) -> None:
    parent = path.parent
    try:
        parent.rmdir()
    except OSError:
        return
    try:
        parent.parent.rmdir()
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


def ingest_rows(cur: sqlite3.Cursor, rows: Iterable[dict], existing_urls: set[str]) -> tuple[int, int]:
    inserted, skipped = 0, 0
    for row in rows:
        url = row.get("url")
        symbol = row.get("symbol")

        if url and url in existing_urls:
            skipped += 1
            continue

        if symbol:
            cur.execute("INSERT OR IGNORE INTO symbol(symbol) VALUES (?)", (symbol,))

        cur.execute(
            """
            INSERT INTO article(date, titre, url, source, symbol, name, price, market_cap, coin_circulating)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.get("date"),
                row.get("titre"),
                url,
                row.get("source"),
                symbol,
                row.get("name"),
                row.get("price"),
                row.get("market_cap"),
                row.get("coin_circulating"),
            ),
        )

        inserted += 1
        if url:
            existing_urls.add(url)

    return inserted, skipped


def process_file(cur: sqlite3.Cursor, path: Path, existing_urls: set[str]) -> tuple[int, int]:
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
    inserted, skipped = ingest_rows(cur, payload.to_dict("records"), existing_urls)
    LOGGER.info("File %s: inserted=%s skipped=%s", path, inserted, skipped)

    retain_file(path)

    return inserted, skipped


def refresh_existing_urls(cur: sqlite3.Cursor) -> set[str]:
    cur.execute("SELECT url FROM article WHERE url IS NOT NULL")
    return {row[0] for row in cur.fetchall()}


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
        existing_urls = refresh_existing_urls(cur)
        inserted_total = 0
        skipped_total = 0

        for file_path in files:
            inserted, skipped = process_file(cur, file_path, existing_urls)
            inserted_total += inserted
            skipped_total += skipped

        con.commit()
        LOGGER.info("Cycle stats: inserted=%s skipped=%s", inserted_total, skipped_total)
    finally:
        con.close()


def main() -> None:
    LOGGER.info("Feeder starting with OUT_DIR=%s DB=%s interval=%ss", OUT_DIR, DB_PATH, POLL_SECONDS)

    try:
        while True:
            start = time.time()
            run_cycle()
            duration = time.time() - start
            sleep_time = max(POLL_SECONDS - duration, 0)
            if sleep_time:
                time.sleep(sleep_time)
    except KeyboardInterrupt:
        LOGGER.info("Shutdown requested")


if __name__ == "__main__":
    main()