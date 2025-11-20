import os, time, pathlib
import polars as pl
from loguru import logger

METRICS_ROOT = pathlib.Path(os.getenv("METRICS_ROOT", "../../data/metrics"))
GRANULARITY  = os.getenv("DELTA_GRANULARITY", "tumbling-1h")
THRESHOLD_PCT = float(os.getenv("TRENDING_THRESHOLD_PCT", "50"))

SRC_DIR  = METRICS_ROOT / "windowed" / GRANULARITY
OUT_DIR  = METRICS_ROOT / "delta" / GRANULARITY
def load_windowed() -> pl.DataFrame:
    patt = str(SRC_DIR / "*.parquet")
    try:
        df = pl.read_parquet(patt)
    except Exception as e:
        raise RuntimeError(f"Aucun parquet lisible dans {patt} ({e})")

    need = {"window_start", "window_end", "count"}
    missing = need - set(df.columns)
    if missing:
        raise RuntimeError(f"Colonnes manquantes dans {patt}: {missing}")
    if "symbol" not in df.columns:
        df = df.with_columns(pl.lit(None).cast(pl.Utf8).alias("symbol"))
    if "price" not in df.columns:
        df = df.with_columns(pl.lit(None).cast(pl.Float64).alias("price"))

    df = df.with_columns([
        pl.col("window_start").cast(pl.Datetime(time_zone="UTC")),
        pl.col("window_end").cast(pl.Datetime(time_zone="UTC")),
        pl.col("count").cast(pl.Int64),
        pl.col("symbol").cast(pl.Utf8),
        pl.col("price").cast(pl.Float64),
    ]).sort(["symbol", "window_start"])

    return df
def compute_delta(df: pl.DataFrame) -> pl.DataFrame:
    df = df.sort(["symbol", "window_start"])
    df = df.with_columns([
        pl.col("price").shift(1).over("symbol").alias("prev_price"),
    ])
    df = df.with_columns([
        (pl.col("price") - pl.col("prev_price")).alias("delta"),
    ])
    df = df.with_columns([
        pl.when((pl.col("prev_price").is_not_null()) & (pl.col("prev_price") != 0))
          .then(
              (pl.col("delta").cast(pl.Float64) / pl.col("prev_price").cast(pl.Float64)) * 100.0
          )
          .otherwise(None)
          .alias("delta_pct")
    ])
    df = df.with_columns([
        (pl.col("delta_pct") > THRESHOLD_PCT).fill_null(False).alias("trending_up")
    ])
    return df.select([
        "symbol",
        "window_start",
        "window_end",
        "price",
        "prev_price",
        "delta",
        "delta_pct",
        "trending_up",
    ])


def write_parquet(df: pl.DataFrame) -> str:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    outpath = OUT_DIR / f"part-{int(time.time())}.parquet"
    df.write_parquet(outpath)
    return str(outpath)

def main():
    logger.remove(); logger.add(lambda m: print(m, end=""))
    logger.info(f'{{"service":"builder","msg":"delta_start","granularity":"{GRANULARITY}","threshold_pct":{THRESHOLD_PCT}}}')
    try:
        base = load_windowed()
    except Exception as e:
        logger.error(f'{{"service":"builder","msg":"delta_load_failed","error":"{str(e)}"}}')
        return

    if base.height == 0:
        logger.warning('{"service":"builder","msg":"delta_empty_source"}')
        return

    df = compute_delta(base)
    outpath = write_parquet(df)
    logger.info(f'{{"service":"builder","msg":"delta_written","rows":{df.height},"path":"{outpath}"}}')

if __name__ == "__main__":
    main()
