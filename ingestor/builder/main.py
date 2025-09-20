import os, time, json, hashlib, pathlib
from datetime import datetime, timezone
from loguru import logger
import polars as pl
RAW_DIR = pathlib.Path(os.getenv("RAW_DIR", "../data/raw"))
OUT_DIR = pathlib.Path(os.getenv("OUT_DIR", "../data/clean/parquet"))

SLEEP_SEC = int(os.getenv("BUILDER_POLL_INTERVAL", "5"))

def ensure_cols(df: pl.DataFrame, cols: list[str]) -> pl.DataFrame:
    for c in cols:
        if c not in df.columns:
            df = df.with_columns(pl.lit(None).alias(c))
    return df
import io
import codecs

def process_file(path: pathlib.Path) -> int:
    with open(path, "rb") as f:
        raw = f.read()
    if raw[:3] == codecs.BOM_UTF8:
        raw = raw[3:]
    text = raw.decode("utf-8", errors="replace")
    df = pl.read_ndjson(io.StringIO(text))
    if df.is_empty():
        logger.info(json.dumps({
            "service":"builder","level":"debug","msg":"empty_file", "path": str(path)
        }))
        return 0
    df = ensure_cols(df, ["title","url","source","published_at","fetched_at"])
    df = df.with_columns(
        pl.struct(["url","title"]).map_elements(
            lambda r: hashlib.sha1(((r["url"] or "") + (r["title"] or "")).encode("utf-8")).hexdigest()
        ).alias("id")
    )

    df = df.with_columns([
        pl.when(pl.col("published_at").is_not_null())
        .then(
            pl.col("published_at")
            .str.replace(r"Z$", "+00:00")  # 'Z' -> '+00:00'
            .str.strptime(pl.Datetime, format="%Y-%m-%dT%H:%M:%S%z", strict=False)
            .dt.convert_time_zone("UTC")  # normalise en UTC
        )
        .otherwise(None)
        .alias("ts")
    ]).with_columns([
        pl.col("ts").dt.date().alias("date")
    ])
    df = df.select(["id","ts","date","title","url","source","fetched_at"])
    total = 0
    for key, g in df.group_by("date"):
        date_value = key[0] if isinstance(key, tuple) else key
        try:
            folder = date_value.isoformat()
        except AttributeError:
            folder = str(date_value)

        outdir = OUT_DIR / f"date={folder}"
        outdir.mkdir(parents=True, exist_ok=True)
        outpath = outdir / f"part-{int(time.time())}.parquet"
        g.write_parquet(outpath)
        logger.info(json.dumps({
            "service": "builder", "level": "info", "msg": "parquet_written",
            "date": folder, "rows": g.height, "path": str(outpath)
        }))

    return total

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    processed: set[pathlib.Path] = set()
    logger.remove()
    logger.add(lambda m: print(m, end=""))
    logger.info(json.dumps({
        "service":"builder","level":"info","msg":"start",
        "raw_dir": str(RAW_DIR.resolve()),
        "out_dir": str(OUT_DIR.resolve()),
        "ts": datetime.now(timezone.utc).isoformat()
    }))

    while True:
        files = sorted(RAW_DIR.glob("*/*/*/*.ndjson"))
        logger.info(json.dumps({
            "service":"builder","level":"debug","msg":"scan_iteration",
            "raw_dir": str(RAW_DIR.resolve()),
            "found_files": len(files),
            "already_processed": len(processed),
            "ts": datetime.now(timezone.utc).isoformat()
        }))

        for p in files:
            if p in processed:
                continue
            logger.info(json.dumps({
                "service":"builder","level":"debug","msg":"new_file_detected",
                "path": str(p),
                "ts": datetime.now(timezone.utc).isoformat()
            }))
            try:
                n = process_file(p)
                logger.info(json.dumps({
                    "service":"builder","level":"info","msg":"file_processed",
                    "path": str(p), "rows": n,
                    "ts": datetime.now(timezone.utc).isoformat()
                }))
                processed.add(p)
            except Exception as e:
                logger.error(json.dumps({
                    "service":"builder","level":"error","msg":"process_failed",
                    "path": str(p), "error": str(e),
                    "ts": datetime.now(timezone.utc).isoformat()
                }))
        time.sleep(SLEEP_SEC)

if __name__ == "__main__":
    main()
