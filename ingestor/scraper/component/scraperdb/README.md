# DuckDB – Schéma minimal

Actuellement : création des tables et index partagés avec l'API (`duckdb_client`).

Tables créées :
1. articles
2. metrics_windowed
3. metrics_delta
4. metrics_sources_daily
5. metrics_trending
6. latest

## 1. Pré-requis et installation
```bash
cd ingestor
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 2. Créer / initialiser le schéma
```bash
python3 -m scrapper.scraperdb.duck_schema
```
La fonction `init_schema()` est désormais réutilisée par l'API pour s'assurer que
le schema est à jour avant l'ingestion des Parquet.

## 3. Vérifier les tables
```bash
duckdb data/duck/warehouse.duckdb "SHOW TABLES;"
duckdb data/duck/warehouse.duckdb "DESCRIBE articles;"
```

## 4. Variable d'environnement
| Var | Défaut | Description |
|-----|--------|-------------|
| DUCKDB_FILE | ../data/duck/warehouse.duckdb | Emplacement du fichier DuckDB |

