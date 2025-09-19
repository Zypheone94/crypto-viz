import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Set, Tuple

from .models import ArticleModel


def _partition_path(base_dir: str, dt: datetime) -> Path:
    d = dt.astimezone(timezone.utc)
    return Path(base_dir) / "data" / "raw" / f"{d.year:04d}" / f"{d.month:02d}" / f"{d.day:02d}"


def _load_existing_hashes(partition_dir: Path) -> Set[str]:
    seen: Set[str] = set()
    if not partition_dir.exists():
        return seen
    for file in partition_dir.glob("part-*.ndjson"):
        try:
            with file.open("r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        obj = json.loads(line)
                        if isinstance(obj, dict) and "id" in obj:
                            seen.add(obj["id"])
                    except Exception:
                        continue
        except Exception:
            continue
    return seen


def write_ndjson(base_dir: str, items: Iterable[ArticleModel]) -> Tuple[int, Path]:
    items = list(items)
    if not items:
        return 0, Path(base_dir)

    fetched_dt = max(i.fetched_at for i in items)
    partition_dir = _partition_path(base_dir, fetched_dt)
    partition_dir.mkdir(parents=True, exist_ok=True)

    seen = _load_existing_hashes(partition_dir)

    ts = int(datetime.now(timezone.utc).timestamp())
    out_file = partition_dir / f"part-{ts}.ndjson"

    written = 0
    with out_file.open("w", encoding="utf-8") as f:
        for item in items:
            if item.id in seen:
                continue
            # Pydantic v1/v2 compatible serialization
            try:
                line = item.model_dump_json()
            except AttributeError:
                line = item.json()
            f.write(line + "\n")
            seen.add(item.id)
            written += 1

    return written, out_file


