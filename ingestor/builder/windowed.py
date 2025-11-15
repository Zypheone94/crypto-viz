import os, time, pathlib
import polars as pl
from loguru import logger

CLEAN_ROOT   = pathlib.Path(os.getenv("CLEAN_ROOT", "../../data/clean/parquet"))
METRICS_ROOT = pathlib.Path(os.getenv("METRICS_ROOT", "../../data/metrics/windowed"))
def load_lazy() -> pl.LazyFrame:
    patt = str(CLEAN_ROOT / "**" / "*.parquet")
    lf = pl.scan_parquet(patt)
    schema = lf.collect_schema()
    names = schema.names()
    if "fetched_at" not in names:
        raise RuntimeError(f"'fetched_at' column not found in {patt}")
    if "symbol" not in names:
        raise RuntimeError(f"'symbol' column not found in {patt}")
    if "price" not in names:
        raise RuntimeError(f"'price' column not found in {patt}")
    if schema["fetched_at"] == pl.Datetime:
        ts_expr = pl.col("fetched_at")
    else:
        ts_expr = (
            pl.col("fetched_at")
              .cast(pl.Utf8)
              .str.replace(r"Z$", "+00:00")
              .str.strptime(pl.Datetime, strict=False)
        )

    lf = lf.select(
        ts_expr.dt.replace_time_zone("UTC").alias("ts"),
        pl.col("symbol").cast(pl.Utf8),
        pl.col("price").cast(pl.Float64),
    )
    lf = lf.filter(pl.col("ts").is_not_null())
    return lf


def _normalize_boundaries(df: pl.DataFrame) -> pl.DataFrame:
    rename = {}
    if "_lower_boundary" in df.columns: rename["_lower_boundary"] = "window_start"
    if "_upper_boundary" in df.columns: rename["_upper_boundary"] = "window_end"
    if rename:
        df = df.rename(rename)

    for c in ("window_start", "window_end"):
        if c in df.columns:
            df = df.with_columns(pl.col(c).cast(pl.Datetime(time_zone="UTC")))
    if "count" in df.columns:
        df = df.with_columns(pl.col("count").cast(pl.Int64))
    if "window_start" in df.columns:
        df = df.sort("window_start")

    return df

def _period_to_kwargs(period: str) -> dict:
    if period.endswith("h"):
        return {"hours": int(period[:-1])}
    if period.endswith("m"):
        return {"minutes": int(period[:-1])}
    if period.endswith("d"):
        return {"days": int(period[:-1])}
    raise ValueError(f"Unsupported period: {period}")
def compute_window(lf: pl.LazyFrame, *, every: str, period: str) -> pl.DataFrame:
    out = (
        lf.sort("fetched_at")
          .group_by_dynamic(
              index_column="fetched_at",
              every=every,
              period=period,
              closed="left",
              include_boundaries=True,
              label="left",
              group_by="symbol",
          )
          .agg([
              pl.len().alias("count"),
              pl.col("price").last().alias("price"),
          ])
    )
    df = out.collect()
    df = _normalize_boundaries(df)
    if "window_start" not in df.columns:
        if "ts" in df.columns:
            df = df.rename({"ts": "window_start"})
        df = df.with_columns(
            (pl.col("window_start") + pl.duration(**_period_to_kwargs(period))).alias("window_end")
        )
    return df.select(
        ["symbol", "window_start", "window_end", "count", "price"]
    ).sort(["symbol", "window_start"])


def write_parquet(df: pl.DataFrame, granularity: str) -> None:
    outdir = METRICS_ROOT / granularity
    outdir.mkdir(parents=True, exist_ok=True)
    outpath = outdir / f"part-{int(time.time())}.parquet"
    df.write_parquet(outpath)
    logger.info(f"[windowed] wrote {df.height} rows -> {outpath}")

def main():
    logger.remove(); logger.add(lambda m: print(m, end=""))

    try:
        lf = load_lazy()
    except Exception as e:
        logger.warning(f"[windowed] nothing to process ({e})")
        return

    t1h = compute_window(lf, every="1h", period="1h")
    if t1h.height > 0:
        write_parquet(t1h, "tumbling-1h")
    else:
        logger.info("[windowed] tumbling-1h -> empty")

    t1d = compute_window(lf, every="1d", period="1d")
    if t1d.height > 0:
        write_parquet(t1d, "tumbling-1d")
    else:
        logger.info("[windowed] tumbling-1d -> empty")

    s1h30 = compute_window(lf, every="30m", period="1h")
    if s1h30.height > 0:
        write_parquet(s1h30, "sliding-1h-step-30m")
    else:
        logger.info("[windowed] sliding-1h-step-30m -> empty")

if __name__ == "__main__":
    main()
