import os, time, json, hashlib, pathlib, io, codecs, re
from datetime import datetime, timezone
from loguru import logger
import polars as pl
from algo import average

RAW_DIR = pathlib.Path(os.getenv("RAW_DIR", "../data/raw"))
OUT_DIR = pathlib.Path(os.getenv("OUT_DIR", "../data/clean/parquet"))
REJECT_DIR = OUT_DIR.parent / "_corrupt"
SLEEP_SEC = int(os.getenv("BUILDER_POLL_INTERVAL", "5"))

def _clean_text(s: str | None) -> str | None:
    if s is None:
        return None
    s = s.encode("utf-8", errors="ignore").decode("utf-8")
    s = re.sub(r"\s+", " ", s.strip())
    return s

def _sha1_from(title: str | None, url: str | None) -> str:
    return hashlib.sha1(((url or "") + (title or "")).encode("utf-8")).hexdigest()

def ensure_cols(df: pl.DataFrame, cols: list[str]) -> pl.DataFrame:
    for c in cols:
        if c not in df.columns:
            df = df.with_columns(pl.lit(None).alias(c))
    return df

def process_file(path: pathlib.Path) -> int:
    raw = path.read_bytes()
    if raw[:3] == codecs.BOM_UTF8:
        raw = raw[3:]
    text = raw.decode("utf-8", errors="replace")
    df = pl.read_ndjson(io.StringIO(text))

    if df.is_empty():
        logger.info(json.dumps({"service":"builder","level":"debug","msg":"empty_file","path":str(path)}))
        return 0

    expected = [
        "title","url","source","published_at","fetched_at",
        "symbol","price_usd","market_cap_usd","id"
    ]
    df = ensure_cols(df, expected)

    if "id" not in df.columns:
        df = df.with_columns(pl.lit(None).alias("id"))
    df = df.with_columns(
        pl.when(pl.col("id").is_null() | (pl.col("id")==""))
          .then(pl.struct(["url","title"]).map_elements(lambda r: _sha1_from(r["title"], r["url"])))
          .otherwise(pl.col("id"))
          .alias("id")
    )
    df = df.with_columns([
        pl.when(pl.col("published_at").is_not_null())
          .then(
              pl.col("published_at").cast(pl.Utf8)
              .str.replace(r"Z$", "+00:00")
              .str.strptime(pl.Datetime, format="%Y-%m-%dT%H:%M:%S%z", strict=False)
              .dt.convert_time_zone("UTC")
          ).otherwise(None).alias("ts"),
        pl.when(pl.col("fetched_at").is_not_null())
          .then(
              pl.col("fetched_at").cast(pl.Utf8)
              .str.replace(r"Z$", "+00:00")
              .str.strptime(pl.Datetime, format="%Y-%m-%dT%H:%M:%S%z", strict=False)
              .dt.convert_time_zone("UTC")
          ).otherwise(None).alias("fetched_at_ts"),
    ])
    invalid = (
        df.filter(pl.col("ts").is_null())
          .with_columns(pl.col("published_at").alias("_corrupt_record"))
          .select(["id","title","url","source","published_at","fetched_at","symbol","price_usd","market_cap_usd","_corrupt_record"])
    )
    valid = df.filter(pl.col("ts").is_not_null())

    valid = (
        valid.with_columns([
            pl.col("title").map_elements(_clean_text, return_dtype=pl.Utf8),
            pl.col("url").cast(pl.Utf8).map_elements(_clean_text, return_dtype=pl.Utf8),
            pl.col("source").cast(pl.Utf8).map_elements(_clean_text, return_dtype=pl.Utf8),
            pl.col("symbol").cast(pl.Utf8).map_elements(_clean_text, return_dtype=pl.Utf8),

            pl.col("price_usd").cast(pl.Float64),
            pl.col("market_cap_usd").cast(pl.Float64),

            # dates
            pl.col("ts").alias("ts"),  # déjà UTC
            pl.col("ts").dt.date().alias("date"),
            pl.col("fetched_at_ts").alias("fetched_at"),
        ])
        .select([
            "id","ts","date","title","url","source","fetched_at",
            "symbol","price_usd","market_cap_usd"
        ])
    )

    if invalid.height > 0:
        REJECT_DIR.mkdir(parents=True, exist_ok=True)
        rej_path = REJECT_DIR / f"reject-{int(time.time())}.ndjson"
        with open(rej_path, "w", encoding="utf-8") as f:
            for rec in invalid.to_dicts():
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        logger.warning(json.dumps({
            "service":"builder","level":"warn","msg":"corrupt_rows",
            "count": invalid.height, "reject_file": str(rej_path)
        }))

    total = 0
    for key, g in valid.group_by("date"):
        date_value = key[0] if isinstance(key, tuple) else key
        folder = getattr(date_value, "isoformat", lambda: str(date_value))()
        outdir = OUT_DIR / f"date={folder}"
        outdir.mkdir(parents=True, exist_ok=True)
        outpath = outdir / f"part-{int(time.time())}.parquet"
        g.write_parquet(outpath)
        logger.info(json.dumps({
            "service":"builder","level":"info","msg":"parquet_written",
            "date":folder,"rows":g.height,"path":str(outpath)
        }))
        total += g.height

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
