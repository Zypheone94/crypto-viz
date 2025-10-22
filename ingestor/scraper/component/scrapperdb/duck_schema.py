from __future__ import annotations

import os
import pathlib
from glob import glob
from typing import Iterable, List

import duckdb

DEFAULT_PARQUET_DIR = (
    pathlib.Path(__file__).resolve().parents[1] / "data" / "clean" / "parquet"
)
PARQUET_DIR = pathlib.Path(
    os.getenv("CRYPTO_VIZ_PARQUET_DIR", str(DEFAULT_PARQUET_DIR))
).resolve()
PARQUET_GLOB = os.getenv(
    "CRYPTO_VIZ_PARQUET_GLOB", f"{PARQUET_DIR.as_posix()}/**/*.parquet"
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO_ROOT / "scraper" / "data" / "duck" / "warehouse.duckdb"
WAREHOUSE_DB = pathlib.Path(os.getenv("CRYPTO_VIZ_WAREHOUSE_DB", str(DEFAULT_DB))).resolve()

WINDOW_LABEL = "1h"
BASELINE_LABEL = "24h"


def ensure_physical_tables(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("""
        CREATE OR REPLACE TABLE articles (
                id         VARCHAR,
                ts         TIMESTAMP,
                date       DATE,
                title      VARCHAR,
                url        VARCHAR,
                source     VARCHAR,
                fetched_at TIMESTAMP
            );
    """)

    con.execute("""
        CREATE OR REPLACE TABLE metrics_windowed (
            window_start TIMESTAMP,
            window_end   TIMESTAMP,
            source       VARCHAR,
            count        BIGINT
        );
    """)

    con.execute("""
        CREATE OR REPLACE TABLE metrics_delta (
            source         VARCHAR,
            window_label   VARCHAR,
            baseline_label VARCHAR,
            as_of          TIMESTAMP,
            current_count  BIGINT,
            prev_count     BIGINT,
            delta          BIGINT,
            delta_pct      DOUBLE
        );
    """)

    con.execute("""
        CREATE OR REPLACE TABLE metrics_sources_daily (
            date   DATE,
            source VARCHAR,
            count  BIGINT
        );
    """)

    con.execute("""
        CREATE OR REPLACE TABLE metrics_trending (
            rank           INTEGER,
            source         VARCHAR,
            window_label   VARCHAR,
            baseline_label VARCHAR,
            as_of          TIMESTAMP,
            value          BIGINT,
            prev           BIGINT,
            delta          BIGINT,
            delta_pct      DOUBLE
        );
    """)

    con.execute("""
        CREATE OR REPLACE TABLE latest (
            source       VARCHAR,
            window_label VARCHAR,
            updated_at   TIMESTAMP,
            count        BIGINT
        );
    """)


def _truncate_all(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("TRUNCATE TABLE articles;")
    con.execute("TRUNCATE TABLE metrics_windowed;")
    con.execute("TRUNCATE TABLE metrics_delta;")
    con.execute("TRUNCATE TABLE metrics_sources_daily;")
    con.execute("TRUNCATE TABLE metrics_trending;")
    con.execute("TRUNCATE TABLE latest;")


def _format_file_array(files: Iterable[str]) -> str:
    quoted = [ "'" + pathlib.Path(p).resolve().as_posix().replace("'", "''") + "'" for p in files ]
    return "[" + ", ".join(quoted) + "]"


def rebuild_from_parquet(con: duckdb.DuckDBPyConnection, parquet_files: List[str]) -> None:
    ensure_physical_tables(con)
    _truncate_all(con)

    if not parquet_files:
        print(f"[WARN] Aucun .parquet trouvé via GLOB: {PARQUET_GLOB}. Tables vidées mais non remplies.")
        return

    file_array_sql = _format_file_array(sorted(parquet_files))

    # 1) ARTICLES (dedup by id, keep latest ts)
    con.execute(
        f"""
            INSERT INTO articles (id, ts, date, title, url, source, fetched_at)
            WITH raw AS (
                SELECT
                    id,
                    COALESCE(
                        TRY_CAST(ts AS TIMESTAMP),
                        TRY_STRPTIME(CAST(ts AS VARCHAR), '%Y-%m-%dT%H:%M:%S%z')
                    ) AS ts,
                    COALESCE(
                        TRY_CAST(date AS DATE),
                        CAST(
                            COALESCE(
                                TRY_CAST(ts AS TIMESTAMP),
                                TRY_STRPTIME(CAST(ts AS VARCHAR), '%Y-%m-%dT%H:%M:%S%z')
                            ) AS DATE
                        )
                    ) AS date,
                    title,
                    url,
                    source,
                    TRY_CAST(fetched_at AS TIMESTAMP) AS fetched_at
                FROM read_parquet({file_array_sql}, union_by_name=True)
            ), dedup AS (
                SELECT * FROM raw
                WHERE id IS NOT NULL AND ts IS NOT NULL
                QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY ts DESC) = 1
            )
            SELECT id, ts, date, title, url, source, fetched_at FROM dedup;
        """
    )

    # 2) metrics_windowed (daily buckets, by source)
    con.execute(
        """
            INSERT INTO metrics_windowed
            SELECT
                window_start,
                window_start + INTERVAL 1 DAY AS window_end,
                source,
                COUNT(*) AS count
            FROM (
                SELECT date_trunc('day', ts) AS window_start, source
                FROM articles
                WHERE ts IS NOT NULL AND source IS NOT NULL
            )
            GROUP BY window_start, source
            ORDER BY window_start, source;
        """
    )

    # 3) metrics_delta (per source: last 1h vs previous 24h)
    con.execute(
        f"""
        INSERT INTO metrics_delta
        WITH recent AS (
            SELECT source, COUNT(*) AS current_count
            FROM articles
            WHERE ts >= current_timestamp - INTERVAL 1 HOUR
            GROUP BY source
        ),
        baseline AS (
            SELECT source, COUNT(*) AS prev_count
            FROM articles
            WHERE ts <  current_timestamp - INTERVAL 1 HOUR
              AND ts >= current_timestamp - INTERVAL 25 HOUR
            GROUP BY source
        ),
        merged AS (
            SELECT
                COALESCE(r.source, b.source) AS source,
                '{WINDOW_LABEL}'  AS window_label,
                '{BASELINE_LABEL}' AS baseline_label,
                current_timestamp AS as_of,
                COALESCE(r.current_count, 0) AS current_count,
                COALESCE(b.prev_count, 0)    AS prev_count
            FROM recent r
            FULL OUTER JOIN baseline b USING (source)
        )
        SELECT
            source,
            window_label,
            baseline_label,
            as_of,
            current_count,
            prev_count,
            current_count - prev_count AS delta,
            CASE WHEN prev_count = 0 THEN NULL
                 ELSE (current_count - prev_count)::DOUBLE / prev_count
            END AS delta_pct
        FROM merged
        ORDER BY delta_pct DESC NULLS LAST, source;
        """
    )

    # 4) metrics_sources_daily (simple volume par jour/source)
    con.execute(
        """
        INSERT INTO metrics_sources_daily
        SELECT date, source, COUNT(*) AS count
        FROM articles
        GROUP BY date, source
        ORDER BY date, source;
        """
    )

    # 5) metrics_trending – ranking basé sur metrics_delta (delta_pct DESC)
    con.execute(
        """
        INSERT INTO metrics_trending
        WITH ranked AS (
            SELECT
                ROW_NUMBER() OVER (ORDER BY delta_pct DESC NULLS LAST, source) AS rank,
                source,
                window_label,
                baseline_label,
                as_of,
                current_count AS value,
                prev_count    AS prev,
                (current_count - prev_count) AS delta,
                delta_pct
            FROM metrics_delta
        )
        SELECT
            rank, source, window_label, baseline_label, as_of, value, prev, delta, delta_pct
        FROM ranked
        ORDER BY rank;
        """
    )

    # 6) latest snapshot (per source + total) with window label
    con.execute(
        f"""
        INSERT INTO latest(source, window_label, updated_at, count)
        SELECT
            metric_source AS source,
            '{WINDOW_LABEL}' AS window_label,
            updated_at,
            count
        FROM (
            SELECT source AS metric_source,
                   COUNT(*) AS count,
                   MAX(ts)  AS updated_at
            FROM articles
            GROUP BY source
            UNION ALL
            SELECT 'total' AS metric_source,
                   COUNT(*) AS count,
                   MAX(ts)  AS updated_at
            FROM articles
        );
        """
    )


if __name__ == "__main__":
    WAREHOUSE_DB.parent.mkdir(parents=True, exist_ok=True)

    # Resolve parquet files from GLOB (recursive)
    files = glob(PARQUET_GLOB, recursive=True)

    print(f"[INFO] Target DB     : {WAREHOUSE_DB}")
    print(f"[INFO] Parquet GLOB  : {PARQUET_GLOB}")
    print(f"[INFO] Parquet files : {len(files)}")

    with duckdb.connect(str(WAREHOUSE_DB)) as con:
        rebuild_from_parquet(con, files)
        total = con.execute("SELECT COUNT(*) FROM articles;").fetchone()[0]
        delta_rows = con.execute("SELECT COUNT(*) FROM metrics_delta;").fetchone()[0]
        trending_rows = con.execute("SELECT COUNT(*) FROM metrics_trending;").fetchone()[0]
        latest_rows = con.execute("SELECT COUNT(*) FROM latest;").fetchone()[0]

        print(f"[OK] Warehouse rebuilt → {WAREHOUSE_DB}")
        print(f"     articles={total}, metrics_delta={delta_rows}, trending={trending_rows}, latest={latest_rows}")
