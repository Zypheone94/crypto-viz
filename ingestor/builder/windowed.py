import os
import time
import pathlib
import mysql.connector

import pandas as pd
import polars as pl
from loguru import logger


WAREHOUSE_DB = pathlib.Path("ingestor/scraper/component/scraperdb/data/ingestor.db")


SOURCE_TABLE = os.getenv("WINDOWED_SOURCE_TABLE", "article")
TS_COL = os.getenv("WINDOWED_TS_COLUMN", "fetched_at")
SYMBOL_COL = os.getenv("WINDOWED_SYMBOL_COLUMN", "symbol")
PRICE_COL = os.getenv("WINDOWED_PRICE_COLUMN", "price")

METRICS_ROOT = pathlib.Path(
    os.getenv("METRICS_ROOT", "../../data/metrics/windowed")
)

def load_from_db() -> pl.LazyFrame:
    """
    Lit la table SQLite (article par défaut) et retourne un LazyFrame Polars
    avec colonnes: symbol (Utf8), ts (Datetime[UTC]), price (Float64).
    """
    try:
        con = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", "host.docker.internal"),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", ""),
            database=os.getenv("MYSQL_DATABASE", "ingestor")
        )
    except Exception as e:
        logger.error(f"Impossible de se connecter à MySQL : {e}")
        return pl.DataFrame([]).lazy()

    query = f"""
            SELECT
                {SYMBOL_COL} AS symbol,
                {TS_COL}     AS ts,
                {PRICE_COL}  AS price
            FROM {SOURCE_TABLE}
            WHERE {TS_COL} IS NOT NULL
        """

    try:
        cursor = con.cursor(dictionary=True)
        cursor.execute(query)
        rows = cursor.fetchall()
        pdf = pd.DataFrame(rows)
    except Exception as e:
        logger.error(f"Erreur SQL : {e}")
        pdf = pd.DataFrame([])
    finally:
        con.close()

    if pdf.empty:
        return pl.DataFrame([]).lazy()

    # conversion Polars
    df = pl.from_pandas(pdf)

    df = df.with_columns([
        pl.col("symbol").cast(pl.Utf8),
        pl.col("price").cast(pl.Float64),
    ])

    # parse timestamp automatique
    df = df.with_columns(
        pl.col("ts").cast(pl.Utf8).str.strptime(pl.Datetime, strict=False).alias("ts")
    )

    # time zone
    df = df.with_columns(
        pl.col("ts").dt.replace_time_zone("UTC")
    )

    df = df.filter(pl.col("ts").is_not_null())

    return df.lazy()

def _normalize_boundaries(df: pl.DataFrame) -> pl.DataFrame:
    """
    Harmonise les noms de colonnes de fenêtre (Polars peut sortir _lower_boundary / _upper_boundary).
    """
    rename = {}
    if "_lower_boundary" in df.columns:
        rename["_lower_boundary"] = "window_start"
    if "_upper_boundary" in df.columns:
        rename["_upper_boundary"] = "window_end"
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
    """
    Calcule des fenêtres temporelles (tumbling/sliding) par symbol.
    - every: pas entre fenêtres (ex "1h", "30m", "1d")
    - period: durée de la fenêtre (ex "1h", "1d")
    """
    out = (
        lf.sort("ts")
        .group_by_dynamic(
            index_column="ts",
            every=every,
            period=period,
            closed="left",
            include_boundaries=True,
            label="left",
            group_by="symbol",
        )
        .agg(
            [
                pl.len().alias("count"),
                pl.col("price").last().alias("price"),
            ]
        )
    )

    df = out.collect()
    df = _normalize_boundaries(df)

    # fallback si Polars ne renvoie pas window_start/window_end
    if "window_start" not in df.columns:
        if "ts" in df.columns:
            df = df.rename({"ts": "window_start"})
        df = df.with_columns(
            (pl.col("window_start") + pl.duration(**_period_to_kwargs(period))).alias(
                "window_end"
            )
        )

    return df.select(
        ["symbol", "window_start", "window_end", "count", "price"]
    ).sort(["symbol", "window_start"])


def write_parquet(df: pl.DataFrame, granularity: str) -> None:
    """
    Écrit un parquet pour une granularité donnée (tumbling-1h, tumbling-1d, etc.)
    Dans METRICS_ROOT/granularity, sans jamais supprimer les anciens fichiers.
    """
    outdir = METRICS_ROOT / granularity
    outdir.mkdir(parents=True, exist_ok=True)

    outpath = outdir / f"part-{int(time.time())}.parquet"
    df.write_parquet(outpath)
    logger.info(f"[windowed] wrote {df.height} rows -> {outpath}")

def main():
    logger.remove()
    logger.add(lambda m: print(m, end=""))

    try:
        lf = load_from_db()
    except Exception as e:
        logger.warning(f"[windowed] nothing to process from DB ({e})")
        return

    base = lf.collect()
    if base.height == 0:
        logger.info("[windowed] no rows in DB source")
        return

    t10m = compute_window(lf, every="10m", period="10m")
    if t10m.height > 0:
        write_parquet(t10m, "tumbling-10m")
    else:
        logger.info("[windowed] tumbling-10m -> empty")

    t1h = compute_window(lf, every="1h", period="1h")
    if t1h.height > 0:
        write_parquet(t1h, "tumbling-1h")
    else:
        logger.info("[windowed] tumbling-1h -> empty")

if __name__ == "__main__":
    main()
