"""Collect scraper data, store to NDJSON partitions, then push to RabbitMq."""
import json
import os
import sys
import time
import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Iterable

from scraper import run_all


def _ensure_id(item: Dict[str, Any]) -> str:
    base = "|".join([
        item.get("url") or "",
        item.get("symbol") or "",
        item.get("name") or "",
        item.get("fetched_at") or "",
    ])
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def _coerce_fetched_at(item: Dict[str, Any]) -> str:
    raw = item.get("fetched_at")
    if raw:
        try:
            datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return raw
        except ValueError:
            pass
    return datetime.now(timezone.utc).isoformat()


def _partition_path(root: Path, dt: datetime) -> Path:
    return root / f"{dt.year:04d}" / f"{dt.month:02d}" / f"{dt.day:02d}"


def write_ndjson(raw_root: Path, items: Iterable[Dict[str, Any]]) -> Path | None:
    data = list(items)
    if not data:
        return None

    for entry in data:
        entry["fetched_at"] = _coerce_fetched_at(entry)
        entry.setdefault("id", _ensure_id(entry))

    fetched_dt = datetime.fromisoformat(data[0]["fetched_at"].replace("Z", "+00:00"))
    target_dir = _partition_path(raw_root, fetched_dt)
    target_dir.mkdir(parents=True, exist_ok=True)

    ts = int(time.time())
    out_file = target_dir / f"part-{ts}.ndjson"

    with out_file.open("w", encoding="utf-8") as fh:
        for entry in data:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return out_file


def main() -> None:
    project_root = Path(__file__).resolve().parents[4]
    raw_root = project_root / "data" / "raw"

    print(f"[scraper_to_ndjson] project root: {project_root}")
    print(f"[scraper_to_ndjson] raw root: {raw_root}")

    try:
        items = run_all()
    except Exception as exc:
        print(f"[scraper_to_ndjson] error during run_all: {exc}")
        return
    print(f"[scraper_to_ndjson] collected {len(items)} item(s)")

    out_file = write_ndjson(raw_root, items)
    if not out_file:
        print("[scraper_to_ndjson] nothing to write, exiting")
        return

    print(f"[scraper_to_ndjson] wrote NDJSON to {out_file}")

    try:
        res = subprocess.run([
            sys.executable,
            "-m",
            "ingestor.builder.sendtoRabbitMq",
        ], cwd=str(project_root), check=False)
        print(f"[scraper_to_ndjson] sendtorabbitmq exit code: {res.returncode}")
    except Exception as exc:
        print(f"[scraper_to_ndjson] failed to run sendtorabbitmq: {exc}")



FETCH_INTERVAL = int(os.getenv("FETCH_INTERVAL", "60"))

def main_loop():
    while True:
        print("[scheduler] Starting scrape cycle...")
        try:
            main()
        except Exception as e:
            print(f"[scheduler] Error during scraping cycle: {e}")
        print(f"[scheduler] Sleeping for {FETCH_INTERVAL}s...\n")
        time.sleep(FETCH_INTERVAL)

if __name__ == "__main__":
    main_loop()