import os
import re
import time
import pathlib
import datetime as dt
from typing import List, Tuple, Optional

import polars as pl
from loguru import logger

EVENTS_ROOT = pathlib.Path(os.getenv("EVENTS_ROOT", "../data/clean/parquet"))
METRICS_ROOT = pathlib.Path(os.getenv("METRICS_ROOT", "../data/metrics"))
OUT_DIR = METRICS_ROOT / "delta" / "multi"
THRESHOLD_PCT = float(os.getenv("TRENDING_THRESHOLD_PCT", "50"))
EVENTS_GLOB = os.getenv("EVENTS_GLOB", "date=*/*.parquet")
WINDOW_SPECS: List[Tuple[str, dt.timedelta]] = [
    ("last_1h",  dt.timedelta(hours=1)),
    ("last_3h",  dt.timedelta(hours=3)),
    ("last_1d",  dt.timedelta(days=1)),
    ("last_7d",  dt.timedelta(days=7)),
    ("last_30d", dt.timedelta(days=30)),
]

UTC = dt.timezone.utc
DATE_DIR_RE = re.compile(r"date=(\d{4}-\d{2}-\d{2})")

def now_utc() -> dt.datetime:
    return dt.datetime.now(tz=UTC).replace(microsecond=0)

def parse_iso_to_utc(s: Optional[str]) -> Optional[dt.datetime]:
    if not s:
        return None
    s = str(s).strip()
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return dt.datetime.fromisoformat(s).astimezone(UTC)
    except Exception:
        return None

def extract_date_from_path(p: pathlib.Path) -> Optional[dt.date]:
    m = DATE_DIR_RE.search(str(p))
    if m:
        try:
            return dt.date.fromisoformat(m.group(1))
        except ValueError:
            return None
    return None



def iter_event_files() -> List[pathlib.Path]:
    base = EVENTS_ROOT
    patt = str(base / EVENTS_GLOB)
    files = sorted(pathlib.Path().glob(patt))
    return files

def load_events_ts() -> pl.DataFrame:

    files = iter_event_files()
    if not files:
        raise RuntimeError(f"Aucun fichier trouvé dans {EVENTS_ROOT} avec le motif {EVENTS_GLOB}")

    dfs: List[pl.DataFrame] = []
    keep_cols = ["ts", "fetched_at", "published_at"]

    for f in files:
        try:
            df = pl.read_parquet(f, use_pyarrow=False)
        except Exception as e:
            logger.warning(f"[delta] Lecture ignorée {f}: {e}")
            continue

        available = [c for c in keep_cols if c in df.columns]
        if "ts" in df.columns:
            df = df.with_columns(
                pl.col("ts")
                .cast(pl.Datetime(time_zone="UTC", time_unit="us"), strict=False)
                .alias("ts")
            ).select(["ts"])
        elif any(c in df.columns for c in ("fetched_at", "published_at")):
            candidates = []
            if "fetched_at" in df.columns:
                candidates.append(
                    pl.col("fetched_at")
                    .cast(pl.Utf8)
                    .str.replace(r"Z$", "+00:00")
                    .str.strptime(pl.Datetime, strict=False, format="%Y-%m-%dT%H:%M:%S%z")
                )
            if "published_at" in df.columns:
                candidates.append(
                    pl.col("published_at")
                    .cast(pl.Utf8)
                    .str.replace(r"Z$", "+00:00")
                    .str.strptime(pl.Datetime, strict=False, format="%Y-%m-%dT%H:%M:%S%z")
                )
            if candidates:
                ts_col = candidates[0]
                for c in candidates[1:]:
                    ts_col = ts_col.fill_null(c)
                df = df.with_columns(ts_col.alias("_ts_tmp"))
                df = df.with_columns(
                    pl.col("_ts_tmp").dt.replace_time_zone("UTC").alias("ts")
                ).select(["ts"])
            else:
                df = pl.DataFrame()
        else:
            d = extract_date_from_path(f)
            if not d:
                logger.warning(f"[delta] Impossible de déduire la date pour {f}, fichier ignoré.")
                continue
            ts_val = dt.datetime(d.year, d.month, d.day, tzinfo=UTC)
            nrows = 1
            try:
                nrows = pl.read_parquet(f, use_pyarrow=False).height
            except Exception:
                pass
            df = pl.DataFrame({
                "ts": [ts_val] * nrows
            })

        dfs.append(df)

    if not dfs:
        raise RuntimeError("Aucun dataframe exploitable (ts) n'a pu être chargé.")

    big = pl.concat(dfs, how="vertical_relaxed")

    big = (
        big
        .filter(pl.col("ts").is_not_null())
        .with_columns(pl.col("ts").dt.replace_time_zone("UTC"))
        .select(["ts"])
        .sort("ts")
    )
    if big.height == 0:
        raise RuntimeError("Aucun timestamp exploitable après normalisation.")
    return big



def count_in_window(df_ts: pl.DataFrame, start: dt.datetime, end: dt.datetime) -> int:

    sub = df_ts.filter((pl.col("ts") >= pl.lit(start)) & (pl.col("ts") < pl.lit(end)))
    return int(sub.height)

def compute_all_windows(df_ts: pl.DataFrame) -> pl.DataFrame:

    now = now_utc()
    rows = []
    for name, length in WINDOW_SPECS:
        end = now
        start = end - length
        prev_end = start
        prev_start = prev_end - length

        cur = count_in_window(df_ts, start, end)
        prev = count_in_window(df_ts, prev_start, prev_end)
        delta = cur - prev

        if prev and prev != 0:
            delta_pct = (delta / prev) * 100.0
        else:
            delta_pct = None

        trending_up = bool((delta_pct is not None) and (delta_pct > THRESHOLD_PCT))

        rows.append({
            "window_name": name,
            "window_len": int(length.total_seconds()),  # en secondes
            "window_start": start,
            "window_end": end,
            "count": cur,
            "prev_count": prev,
            "delta": delta,
            "delta_pct": float(delta_pct) if delta_pct is not None else None,
            "trending_up": trending_up,
        })

    df = pl.DataFrame(rows).with_columns([
        pl.col("window_start").cast(pl.Datetime(time_zone="UTC")),
        pl.col("window_end").cast(pl.Datetime(time_zone="UTC")),
        pl.lit(now).alias("generated_at").cast(pl.Datetime(time_zone="UTC")),
    ])
    return df


def write_parquet(df: pl.DataFrame) -> str:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    outpath = OUT_DIR / f"part-{int(time.time())}.parquet"
    df.write_parquet(outpath)
    return str(outpath)



def main():
    logger.remove(); logger.add(lambda m: print(m, end=""))
    logger.info(
        f'{{"service":"builder","msg":"delta_multi_start","events_root":"{EVENTS_ROOT}",'
        f'"glob":"{EVENTS_GLOB}","threshold_pct":{THRESHOLD_PCT}}}'
    )
    try:
        df_ts = load_events_ts()
    except Exception as e:
        logger.error(f'{{"service":"builder","msg":"delta_multi_load_failed","error":"{str(e)}"}}')
        return

    if df_ts.height == 0:
        logger.warning('{"service":"builder","msg":"delta_multi_empty_source"}')
        return

    df = compute_all_windows(df_ts)
    outpath = write_parquet(df)
    logger.info(
        f'{{"service":"builder","msg":"delta_multi_written","rows":{df.height},"path":"{outpath}"}}'
    )

if __name__ == "__main__":
    main()
