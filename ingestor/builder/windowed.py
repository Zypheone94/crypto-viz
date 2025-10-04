import os, time, pathlib
import polars as pl
from loguru import logger

CLEAN_ROOT   = pathlib.Path(os.getenv("CLEAN_ROOT", "../data/clean/parquet"))
METRICS_ROOT = pathlib.Path(os.getenv("METRICS_ROOT", "../data/metrics/windowed"))

def load_lazy() -> pl.LazyFrame:
    patt = str(CLEAN_ROOT / "**" / "*.parquet")
    lf = pl.scan_parquet(patt)

    if "ts" not in lf.collect_schema().names():
        raise RuntimeError(f"'ts' column not found in {patt}")

    return lf.select(pl.col("ts").cast(pl.Datetime).alias("ts"))

def _normalize_boundaries(df: pl.DataFrame) -> pl.DataFrame:
    cols = set(df.columns)
    rename = {}
    if "_lower_boundary" in cols: rename["_lower_boundary"] = "window_start"
    if "_upper_boundary" in cols: rename["_upper_boundary"] = "window_end"
    if rename:
        df = df.rename(rename)
    if "window_start" in df.columns and "window_end" in df.columns:
        df = (df
              .with_columns([
                  pl.col("window_start").cast(pl.Datetime),
                  pl.col("window_end").cast(pl.Datetime),
                  pl.col("count").cast(pl.Int64)
              ])
              .sort("window_start"))
    return df


def compute_window(lf: pl.LazyFrame, *, every: str, period: str) -> pl.DataFrame:
    lf_sorted = lf.sort("ts")

    out = (
        lf_sorted.group_by_dynamic(
            index_column="ts",
            every=every,
            period=period,
            closed="left",
            include_boundaries=True,
            label="left",
        )
        .agg(pl.len().alias("count"))
    )

    df = out.collect()
    df = _normalize_boundaries(df)

    if "window_start" not in df.columns:
        if "ts" in df.columns:
            df = df.rename({"ts": "window_start"}).with_columns(
                pl.col("window_start").cast(pl.Datetime)
            )
        df = df.with_columns(
            (pl.col("window_start") + pl.duration(**_period_to_kwargs(period))).alias("window_end")
        ).select(["window_start", "window_end", "count"]).sort("window_start")
    else:
        df = df.select(["window_start", "window_end", "count"])

    return df
def _period_to_kwargs(period: str) -> dict:
    if period.endswith("h"):
        return {"hours": int(period[:-1])}
    if period.endswith("m"):
        return {"minutes": int(period[:-1])}
    if period.endswith("d"):
        return {"days": int(period[:-1])}
    raise ValueError(f"Unsupported period: {period}")

def write_parquet(df: pl.DataFrame, granularity: str):
    outdir = METRICS_ROOT / granularity
    outdir.mkdir(parents=True, exist_ok=True)
    outpath = outdir / f"part-{int(time.time())}.parquet"
    df.write_parquet(outpath)
    logger.info(f"[windowed] wrote {df.height} rows -> {outpath}")

def main():
    logger.remove(); logger.add(lambda m: print(m, end=""))
    lf = load_lazy()

    tumbling_1h = compute_window(lf, every="1h", period="1h")
    write_parquet(tumbling_1h, "tumbling-1h")

    tumbling_1d = compute_window(lf, every="1d", period="1d")
    write_parquet(tumbling_1d, "tumbling-1d")

    sliding_1h_30m = compute_window(lf, every="30m", period="1h")
    write_parquet(sliding_1h_30m, "sliding-1h-step-30m")

if __name__ == "__main__":
    main()
