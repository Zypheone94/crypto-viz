import os, time, pathlib
import polars as pl
from loguru import logger

CLEAN_ROOT   = pathlib.Path(os.getenv("CLEAN_ROOT", "../../data/clean"))
METRICS_ROOT = pathlib.Path(os.getenv("METRICS_ROOT", "../../data/metrics/windowed"))

def load_lazy() -> pl.LazyFrame:
    patt = str(CLEAN_ROOT / "**" / "*.parquet")
    lf = pl.scan_parquet(patt)

    names = lf.collect_schema().names()
    if "fetched_at" not in names:
        raise RuntimeError(f"'ts' column not found in {patt}")

    return lf.select(
        pl.col("fetched_at")
        .str.to_datetime(format="%Y-%m-%dT%H:%M:%S%.f", time_zone="UTC")
        .alias("fetched_at")
    )

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
          )
          .agg(pl.len().alias("count"))
    )

    df = out.collect(streaming=True)
    df = _normalize_boundaries(df)

    if "window_start" not in df.columns:
        if "fetched_at" in df.columns:
            df = df.rename({"fetched_at": "window_start"})
        df = df.with_columns(
            (pl.col("window_start") + pl.duration(**_period_to_kwargs(period))).alias("window_end")
        ).select(["window_start", "window_end", "count"]).sort("window_start")

    return df.select(["window_start", "window_end", "count"])

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
