create and sourcing env : 

all the above command must be execute in the *ingestor* file

```bash
python -m venv .venv
source .venv/bin/activate   # Linux / Mac
.venv\Scripts\activate      # Windows PowerShell
```

then execute this command : 

``` 
pip install -e .
```

if everything is good a file Crypto_Viz.egg-info

## Reset data sources : 

To reset data sources : 

*data/raw*

*data/clean*

*chk*

You need to open your docker scraper terminal and launch this command : 

``` 
python tools/resetdata.py
```

you might see these type of error : "is not dir or dir does not exist" if the dir is already empty

## Refresh the DuckDB warehouse from local Parquet files

The metrics API reads from the DuckDB warehouse stored in `scraper/data/duck/warehouse.duckdb`. When you ingest new raw
NDJSON samples you can rebuild the warehouse manually with the following steps:

1. **Generate Parquet files**
	```bash
	# still inside the virtualenv at the repo root
	python -c "import pathlib, sys; sys.path.append('ingestor/builder'); import main; main.process_file(pathlib.Path('ingestor/data/raw/2025/10/22/test-data.ndjson'))"
	```
	This runs the builder on a sample NDJSON file and writes Parquet shards under `data/clean/parquet/date=YYYY-MM-DD/`.

2. **Rebuild the warehouse**
	```bash
	python -c "import sys; sys.path.append('ingestor/scraper'); from api.utils import duckdb_client; duckdb_client.refresh_warehouse(force=True)"
	```
	The helper looks for Parquet files in `data/clean/parquet/**` (falling back to the ingestor directory if needed),
	recreates the DuckDB tables, and loads a fresh snapshot.

3. **Quick sanity check (optional)**
	```bash
	duckdb ingestor/scraper/data/duck/warehouse.duckdb "SELECT source, count FROM latest ORDER BY source"
	```
	You should see counts for each news source plus the `total` aggregation. Adjust the SQL query as needed for other
	validations.

> ℹ️ The refresh command can be executed at any time; it replaces the warehouse tables with the latest data found in the
> Parquet lake. Set `CRYPTO_VIZ_PARQUET_GLOB` if your Parquet files live in a different location.