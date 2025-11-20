from __future__ import annotations
from pathlib import Path
import duckdb
import polars as pl


DELTA_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "data" / "metrics" / "delta" / "tumbling-1h"
)
WAREHOUSE_DB = (
    Path(__file__).parent.parent.parent
    / "data" / "duck" / "warehouse.duckdb"
)

WINDOW_LABEL = "1h"
BASELINE_LABEL = "prev"
TOP_LIMIT = 100

def read_delta() -> pl.DataFrame:
    patt = str(DELTA_DIR / "*.parquet")
    df = pl.read_parquet(patt)
    need = {"window_start", "window_end", "count", "prev_count", "delta", "delta_pct"}
    missing = need - set(df.columns)
    if missing:
        raise RuntimeError(f"Colonnes manquantes dans {patt}: {missing}")

    # Types + tri
    return (
        df.with_columns([
            pl.col("window_start").cast(pl.Datetime(time_zone="UTC")),
            pl.col("window_end").cast(pl.Datetime(time_zone="UTC")),
            pl.col("count").cast(pl.Int64),
            pl.col("prev_count").cast(pl.Int64),
            pl.col("delta").cast(pl.Int64),
            pl.col("delta_pct").cast(pl.Float64),
        ])
        .sort("window_start")
    )

def to_trending(df: pl.DataFrame) -> pl.DataFrame:
    if df.is_empty():
        return df

    if "source" not in df.columns:
        df = df.with_columns(pl.lit("GLOBAL").alias("source"))

    tr = (
        df.filter(pl.col("delta_pct").is_not_null())
          .with_columns([
              pl.col("delta_pct").rank("dense", descending=True).alias("rank"),
              pl.lit(WINDOW_LABEL).alias("window_label"),
              pl.lit(BASELINE_LABEL).alias("baseline_label"),
              pl.col("window_end").alias("as_of"),
              pl.col("count").alias("value"),
              pl.col("prev_count").alias("prev"),
          ])
          .select(["rank","source","window_label","baseline_label",
                   "as_of","value","prev","delta","delta_pct"])
          .sort(["delta_pct","value"], descending=[True, True])
    )
    return tr.head(TOP_LIMIT) if TOP_LIMIT else tr

def ensure_table(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("""
        CREATE TABLE IF NOT EXISTS metrics_trending (
            rank           INTEGER,
            source         VARCHAR,
            window_label   VARCHAR,
            baseline_label VARCHAR,
            as_of          TIMESTAMP,
            value          BIGINT,
            prev           BIGINT,
            delta          BIGINT,
            delta_pct      DOUBLE
        )
    """)

def load_into_duck(df_tr: pl.DataFrame) -> int:
    WAREHOUSE_DB.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(WAREHOUSE_DB)) as con:
        ensure_table(con)
        con.execute("DELETE FROM metrics_trending")
        if df_tr.is_empty():
            return 0
        con.register("tr", df_tr.to_arrow())
        con.execute("""
            INSERT INTO metrics_trending
            SELECT
              rank::INTEGER, source::VARCHAR,
              window_label::VARCHAR, baseline_label::VARCHAR,
              as_of::TIMESTAMP, value::BIGINT, prev::BIGINT,
              delta::BIGINT, delta_pct::DOUBLE
            FROM tr
        """)
        return con.execute("SELECT COUNT(*) FROM metrics_trending").fetchone()[0]

def main():
    print(f"[trending->duck] DELTA_DIR={DELTA_DIR}")
    print(f"[trending->duck] WAREHOUSE_DB={WAREHOUSE_DB}")
    df_delta = read_delta()
    df_tr = to_trending(df_delta)
    n = load_into_duck(df_tr)
    print(f"[trending->duck] OK: {n} lignes insérées")

if __name__ == "__main__":
    main()
