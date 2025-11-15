"""Automated feeder that pulls cleaned parquet files into the SQLite warehouse."""

from __future__ import annotations

import logging
import os
import shutil
import sqlite3
import time
from pathlib import Path
from typing import Iterable
import math

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


def process_file(cur: sqlite3.Cursor, path: Path, process_func, base_dir: Path = OUT_DIR, normalize: bool = True, retain: bool = True) -> tuple[int, int]:
    frame = load_frame(path)
    if frame is None:
        if retain:
            move_to_reject(path)
        else:
            LOGGER.error("Failed to load file %s", path)
        return 0, 0

    if frame.empty:
        LOGGER.info("Skipping empty parquet %s", path)
        if retain:
            path.unlink(missing_ok=True)
            clean_parent_dirs(path)
        return 0, 0

    payload = normalise_frame(frame) if normalize else frame
    result = process_func(payload)
    LOGGER.info("File %s: inserted=%s skipped=%s", path, result[0], result[1])

    if retain:
        retain_file_with_base(path, base_dir)

    return result


def retain_file_with_base(src: Path, base_dir: Path) -> None:
    if RETAIN_MAX <= 0:
        src.unlink(missing_ok=True)
        clean_parent_dirs(src)
        return

    relative = src.relative_to(base_dir)
    dest = RETAIN_DIR / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), dest)
    prune_retained()
    clean_parent_dirs(src)

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
            skipped_total += skipped

        con.commit()
        LOGGER.info("Cycle stats: inserted=%s skipped=%s", inserted_total, skipped_total)
    finally:
        con.close()


def manage_delta_files() -> list[Path]:
    files = find_parquet_files(DELTA_PARQUET_DIR)
    if not files:
        LOGGER.info("No delta parquet files found under %s", DELTA_PARQUET_DIR)
        return []

    files_sorted = sorted(files, key=lambda p: p.stat().st_mtime)

    if len(files_sorted) < 2:
        LOGGER.info("Only %s delta file(s), waiting for more before processing", len(files_sorted))
        return []

    file_to_process = files_sorted[0]
    LOGGER.info("Processing oldest delta file: %s (keeping %s newer file(s))",
                file_to_process.name, len(files_sorted) - 1)

    return [file_to_process]

def populate_delta_parquets() -> None:
    windowed_main()
    delta_main()
    populate_delta_table()


def feed_delta_table(cur: sqlite3.Cursor, rows: Iterable[dict]) -> tuple[int, int]:
    inserted = 0
    skipped = 0
    for row in rows:
        try:
            symbol = row.get('symbol')
            window_start = row.get('window_start')
            window_end = row.get('window_end')
            delta = row.get('delta')
            delta_pct = row.get('delta_pct')

            if delta is None or delta_pct is None or delta == '' or delta_pct == '':
                skipped += 1
                continue

            try:
                if math.isnan(delta) or math.isnan(delta_pct):
                    skipped += 1
                    continue
            except (TypeError, ValueError):
                pass

            if hasattr(window_start, 'isoformat'):
                window_start = window_start.isoformat()
            if hasattr(window_end, 'isoformat'):
                window_end = window_end.isoformat()

            window_label = f"{symbol}_{window_start}_{window_end}"

            cur.execute("""
                        INSERT INTO delta (symbol, date_start, date_end,
                                           window_label, delta, delta_pct)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            symbol,
                            window_start,
                            window_end,
                            window_label,
                            delta,
                            delta_pct
                        ))

            inserted += 1

        except Exception as exc:
            LOGGER.error("Failed to insert delta row: %s", exc)
            skipped += 1
            continue

    return inserted, skipped


def populate_delta_table() -> None:
    files = manage_delta_files()
    if not files:
        return

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    try:
        cur = con.cursor()
        inserted_total = 0
        skipped_total = 0

        def process_feed_delta_table(payload: pd.DataFrame) -> tuple[int, int]:
            return feed_delta_table(cur, payload.to_dict("records"))

        for file_path in files:
            inserted, skipped = process_file(
                cur,
                file_path,
                process_feed_delta_table,
                base_dir=DELTA_PARQUET_DIR,
                normalize=False,
                retain=False
            )
            inserted_total += inserted
            skipped_total += skipped

            file_path.unlink(missing_ok=True)
            LOGGER.info("Deleted processed delta file: %s", file_path.name)

        con.commit()
        LOGGER.info("Delta cycle stats: inserted=%s skipped=%s", inserted_total, skipped_total)

    except Exception as exc:
        LOGGER.error("Failed to populate delta table: %s", exc)
    finally:
        con.close()


def main() -> None:
    LOGGER.info(
        "Feeder starting with OUT_DIR=%s DB=%s interval=%ss",
        OUT_DIR, DB_PATH, POLL_SECONDS
    )

    DELTA_INTERVAL = 3600
    last_delta_time = time.time()

    try:
        while True:
            cycle_start = time.time()
            run_cycle()
            duration = int(time.time() - cycle_start)

            sleep_time = max(0, POLL_SECONDS - duration)
            for _ in range(sleep_time):
                if time.time() - last_delta_time >= DELTA_INTERVAL:
                    LOGGER.info("delta parquets ready (%s seconds elapsed)", DELTA_INTERVAL)
                    populate_delta_parquets()
                    last_delta_time = time.time()

                time.sleep(1)

    except KeyboardInterrupt:
        LOGGER.info("Shutdown requested")

if __name__ == "__main__":
    main()