# Scraper Service

The **`scraper`** service contains the main API of the application.

## Structure

- `scraper/api/` – contains the API endpoints and related logic.  
- `scraper/main.py` – **entry point of the API**.

## Dependencies

- The `scraper` service uses dependencies defined in the **`pyproject.toml`** at the root of the project.  
- These dependencies are **shared with the `builder` service**, avoiding duplication.

## Running the API

The service runs via **FastAPI** and can be started using Docker Compose:

Inside the Docker container, the app listens on port **8000**, which is mapped to **8080** on your host machine.  

- Access the API at: [http://localhost:port]

## Documentation

FastAPI automatically provides **Swagger UI** for testing the API:

- Swagger UI: [http://localhost:port/docs]

## DuckDB integration

- Parquet metrics lake: `ingestor/data/clean/parquet/**`
- Warehouse database (populated automatically): `ingestor/scrapper/data/duck/warehouse.duckdb`
- Inspect via CLI:

```bash
duckdb ingestor/scrapper/data/duck/warehouse.duckdb
```

- Endpoints powered by DuckDB:
	- `GET /metrics/timeseries?from=<ISO>&to=<ISO>&bucket=day|hour`
	- `GET /metrics/latest`
- Warehouse tables available for analytics:
	- `articles`, `metrics_windowed`, `metrics_delta`, `metrics_sources_daily`, `metrics_trending`, `latest`
- Le schéma est défini dans `scrapper/scrapperdb/duck_schema.py` et appliqué automatiquement.

### Vérifier rapidement les métriques exposées

- Après un `refresh_warehouse()`, démarrer l'API puis appeler `GET /metrics/latest` pour contrôler que le snapshot correspond aux derniers Parquet.
- L'endpoint `/metrics/timeseries` accepte `bucket=day|hour` (par défaut `day`) et renvoie directement les agrégations DuckDB sur la période fournie.

### Rafraîchir manuellement le warehouse

- L’ingestion se fait automatiquement quand l’API détecte de nouveaux Parquet.
- Pour forcer un rechargement (ex. après un import manuel) :

```bash
cd ingestor
python - <<'PY'
from scraper.api.utils import duckdb_client
duckdb_client.refresh_warehouse(force=True)
print("Warehouse rechargé dans", duckdb_client.get_warehouse_path())
PY
```

- Variables d’environnement utiles :
	- `CRYPTO_VIZ_BASE_DIR` pour surcharger la racine du projet.
	- `CRYPTO_VIZ_PARQUET_GLOB` si les Parquet sont dans un autre dossier.
	- `CRYPTO_VIZ_WAREHOUSE_DB` pour choisir un autre fichier DuckDB.