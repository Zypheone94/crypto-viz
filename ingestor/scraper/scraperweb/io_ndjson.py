import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Iterable, Set, Tuple, List

from models import ArticleModel


def _partition_path(base_dir: str, dt: datetime) -> Path:
    """Create partition path for date-based directory structure.
    
    Args:
        base_dir: The data directory path (should already point to the data folder)
        dt: The datetime to partition by
        
    Returns:
        Path: base_dir/raw/YYYY/MM/DD
    """
    d = dt.astimezone(timezone.utc)
    return Path(base_dir) / "raw" / f"{d.year:04d}" / f"{d.month:02d}" / f"{d.day:02d}"


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


def write_ndjson(base_dir: str, items: Iterable[ArticleModel], source_prefix: str = None, force_write: bool = False) -> Tuple[int, Path]:
    items = list(items)
    if not items:
        return 0, Path(base_dir)

    fetched_dt = max(i.fetched_at for i in items)
    partition_dir = _partition_path(base_dir, fetched_dt)
    partition_dir.mkdir(parents=True, exist_ok=True)

    # For deduplication, only consider files from the same source if source_prefix is provided
    # Skip deduplication if force_write is True
    seen = set()
    if not force_write:
        if source_prefix:
            # Only load hashes from files with the same source prefix
            for file in partition_dir.glob(f"part-{source_prefix}-*.ndjson"):
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
        else:
            seen = _load_existing_hashes(partition_dir)

    ts = int(datetime.now(timezone.utc).timestamp())
    
    # Add source prefix to filename if provided
    if source_prefix:
        out_file = partition_dir / f"part-{source_prefix}-{ts}.ndjson"
    else:
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


def write_to_cache(base_dir: str, items: Iterable[ArticleModel], source: str) -> Tuple[int, Path]:
    """
    Write articles to a cache file organized by source and date.
    
    Args:
        base_dir: Base directory for file writing
        items: Articles to write
        source: Source name (e.g., "coindesk")
    
    Returns:
        Tuple[int, Path]: Number of items written and path
    """
    items = list(items)
    if not items:
        return 0, Path(base_dir)
        
    # Create cache directory if it doesn't exist
    cache_dir = Path(base_dir) / "data" / "cache" / source
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Use current date (UTC) for cache filename
    now_utc = datetime.now(timezone.utc)
    cache_filename = f"{now_utc.year:04d}-{now_utc.month:02d}-{now_utc.day:02d}.ndjson"
    cache_file = cache_dir / cache_filename
    
    written = 0
    with cache_file.open("w", encoding="utf-8") as f:
        for item in items:
            # Pydantic v1/v2 compatible serialization
            try:
                line = item.model_dump_json()
            except AttributeError:
                line = item.json()
            f.write(line + "\n")
            written += 1
    
    return written, cache_file


def load_from_cache(base_dir: str, source: str, max_age_days: int = 7) -> List[ArticleModel]:
    """
    Load articles from the most recent cache file for a given source.
    
    Args:
        base_dir: Base directory for file reading
        source: Source name (e.g., "coindesk")
        max_age_days: Maximum age in days for cache files to be considered
    
    Returns:
        List[ArticleModel]: List of articles from cache
    """
    cache_dir = Path(base_dir) / "data" / "cache" / source
    if not cache_dir.exists():
        return []
    
    # Find all cache files and sort by filename (which contains the date)
    cache_files = sorted([f for f in cache_dir.glob("*.ndjson")], reverse=True)
    
    # Check if we have any cache files
    if not cache_files:
        return []
    
    # Filter by max age if specified
    if max_age_days > 0:
        now = datetime.now(timezone.utc)
        min_date = now - timedelta(days=max_age_days)
        
        valid_files = []
        for file in cache_files:
            try:
                # Extract date from filename
                date_str = file.stem
                file_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if file_date >= min_date:
                    valid_files.append(file)
            except (ValueError, IndexError):
                # Skip files with invalid naming
                continue
        
        if valid_files:
            cache_files = valid_files
    
    # Use most recent cache file
    latest_cache = cache_files[0]
    
    # Load articles from cache
    articles = []
    try:
        with latest_cache.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        article_dict = json.loads(line)
                        # Mark as fallback
                        article_dict["is_fallback"] = True
                        # Handle both Pydantic v1 and v2
                        try:
                            article = ArticleModel.model_validate(article_dict)  # Pydantic v2
                        except AttributeError:
                            article = ArticleModel.parse_obj(article_dict)  # Pydantic v1
                        articles.append(article)
                    except Exception as e:
                        # Skip invalid entries
                        print(f"Error parsing cache entry: {e}")
    except Exception as e:
        print(f"Error reading cache file {latest_cache}: {e}")
        return []
    
    return articles