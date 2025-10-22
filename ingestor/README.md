# Ingestor

## 1) Environment setup

Run these from the `ingestor` folder:

```bash
python -m venv .venv
source .venv/bin/activate   # Linux / Mac
.venv/Scripts/activate      # Windows PowerShell
pip install -e .
```

You should see a `Crypto_Viz.egg-info` folder if installation succeeded.

## 2) Reset data sources (optional)

This clears local storage:
- data/raw
- data/clean
- chk

From the scraper container:

```bash
python tools/resetdata.py
```

You may see warnings if a directory is already empty.

## 3) Create Parquet data

Option A — Use the builder on an NDJSON sample:

```bash
python -c "import pathlib, sys; sys.path.append('ingestor/builder'); import main; main.process_file(pathlib.Path('ingestor/data/raw/2025/10/22/test-data.ndjson'))"
```

Option B — Generate a tiny Parquet sample with prices (Polars):

```bash
python - <<'PY'
import polars as pl, pathlib as p
from datetime import datetime, timezone, timedelta, date as D
d = '2025-10-22'
t0 = datetime(2025,10,22,9,0,0,tzinfo=timezone.utc)
rows = [
  {'id':'a1','ts':t0,'date':D.fromisoformat(d),'title':'Title 1','url':'https://ex/a1','source':'coindesk','fetched_at':t0,'symbol':'BTC','price_usd':68000.0,'market_cap_usd':1.34e12},
  {'id':'a2','ts':t0+timedelta(minutes=15),'date':D.fromisoformat(d),'title':'Title 2','url':'https://ex/a2','source':'coingecko','fetched_at':t0+timedelta(minutes=15),'symbol':'ETH','price_usd':2450.5,'market_cap_usd':2.9e11},
]
df = pl.DataFrame(rows).with_columns([
  pl.col('ts').cast(pl.Datetime('us','UTC')),
  pl.col('fetched_at').cast(pl.Datetime('us','UTC')),
  pl.col('date').cast(pl.Date),
  pl.col('title').cast(pl.Utf8),
  pl.col('url').cast(pl.Utf8),
  pl.col('source').cast(pl.Utf8),
  pl.col('symbol').cast(pl.Utf8),
  pl.col('price_usd').cast(pl.Float64),
  pl.col('market_cap_usd').cast(pl.Float64),
  pl.col('id').cast(pl.Utf8),
])[[ 'id','ts','date','title','url','source','fetched_at','symbol','price_usd','market_cap_usd' ]]
out = p.Path(f'data/clean/parquet/date={d}')
out.mkdir(parents=True, exist_ok=True)
df.write_parquet(out/'part-test.parquet')
print(out/'part-test.parquet')
PY
```

## 4) Refresh the DuckDB warehouse

The metrics API reads from `scraper/data/duck/warehouse.duckdb`. To reload tables from Parquet:

```bash
python -c "import sys; sys.path.append('ingestor/scraper'); from api.utils import duckdb_client; duckdb_client.refresh_warehouse(force=True)"
```

Notes:
- Parquet discovery looks under `data/clean/parquet/**` in repo root (and ingestor fallback).
- Override with `CRYPTO_VIZ_PARQUET_GLOB` if needed.

## 5) Verify with DuckDB

```bash
duckdb ingestor/scraper/data/duck/warehouse.duckdb "SELECT id, ts, date, title, url, source, fetched_at, symbol, price_usd, market_cap_usd FROM articles ORDER BY ts DESC LIMIT 10;"
```

You should see your rows, including `symbol`, `price_usd`, and `market_cap_usd`.

## 6) Warehouse schema (overview)

- articles: id, ts, date, title, url, source, fetched_at, symbol, price_usd, market_cap_usd
- metrics_windowed: window_start, window_end, source, count
- metrics_delta: source, window_label, baseline_label, as_of, current_count, prev_count, delta, delta_pct
- metrics_sources_daily: date, source, count
- metrics_trending: rank, source, window_label, baseline_label, as_of, value, prev, delta, delta_pct
- latest: source, window_label, updated_at, count