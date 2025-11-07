# Guide de test des routes API

## 🚀 Étapes pour tester l'API

### 1. Insérer des données de test

```bash
cd /Users/alexandrupanta/Documents/crypto-viz/ingestor
python3 scraper/tools/insert_test_data.py
```

Cela va créer :
- 5 symboles (BTC, ETH, SOL, ADA, DOT)
- 50 articles sur 7 jours
- 20 deltas avec variations de prix

### 2. Démarrer l'API FastAPI

```bash
cd /Users/alexandrupanta/Documents/crypto-viz/ingestor
uvicorn scraper.api.main:app --reload --host 0.0.0.0 --port 8000
```

OU si vous avez un fichier main.py différent :

```bash
cd /Users/alexandrupanta/Documents/crypto-viz/ingestor/scraper
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Tester avec le script Python

```bash
# Installer httpx si nécessaire
pip install httpx

# Tester toutes les routes
python3 scraper/tools/test_routes.py

# Tester une seule route
python3 scraper/tools/test_routes.py /metrics/latest
```

### 4. Tester avec curl

#### Test de `/metrics/trending`
```bash
curl -X GET "http://localhost:8000/metrics/trending?from=2025-10-31T00:00:00Z&to=2025-11-07T23:59:59Z&bucket=day&limit=5"
```

#### Test de `/metrics/timeseries`
```bash
curl -X GET "http://localhost:8000/metrics/timeseries?from=2025-10-31T00:00:00Z&to=2025-11-07T23:59:59Z&bucket=day"
```

#### Test de `/metrics/latest`
```bash
curl -X GET "http://localhost:8000/metrics/latest"
```

#### Test de `/metrics/top`
```bash
curl -X GET "http://localhost:8000/metrics/top?from=2025-10-31T00:00:00Z&to=2025-11-07T23:59:59Z&limit=5"
```

#### Test de `/metrics/aggregate`
```bash
curl -X GET "http://localhost:8000/metrics/aggregate?from=2025-10-31T00:00:00Z&to=2025-11-07T23:59:59Z&bucket=day"
```

### 5. Tester avec l'interface Swagger

1. Démarrer l'API
2. Ouvrir dans le navigateur : http://localhost:8000/docs
3. Tester chaque endpoint interactivement

### 6. Tester avec Postman ou Insomnia

#### Collection Postman

Importer cette collection JSON :

```json
{
  "info": {
    "name": "Crypto Viz API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Get Trending",
      "request": {
        "method": "GET",
        "url": {
          "raw": "http://localhost:8000/metrics/trending?from=2025-10-31T00:00:00Z&to=2025-11-07T23:59:59Z&bucket=day&limit=5",
          "host": ["http://localhost:8000"],
          "path": ["metrics", "trending"],
          "query": [
            {"key": "from", "value": "2025-10-31T00:00:00Z"},
            {"key": "to", "value": "2025-11-07T23:59:59Z"},
            {"key": "bucket", "value": "day"},
            {"key": "limit", "value": "5"}
          ]
        }
      }
    },
    {
      "name": "Get Timeseries",
      "request": {
        "method": "GET",
        "url": {
          "raw": "http://localhost:8000/metrics/timeseries?from=2025-10-31T00:00:00Z&to=2025-11-07T23:59:59Z&bucket=day",
          "host": ["http://localhost:8000"],
          "path": ["metrics", "timeseries"],
          "query": [
            {"key": "from", "value": "2025-10-31T00:00:00Z"},
            {"key": "to", "value": "2025-11-07T23:59:59Z"},
            {"key": "bucket", "value": "day"}
          ]
        }
      }
    },
    {
      "name": "Get Latest",
      "request": {
        "method": "GET",
        "url": "http://localhost:8000/metrics/latest"
      }
    },
    {
      "name": "Get Top",
      "request": {
        "method": "GET",
        "url": {
          "raw": "http://localhost:8000/metrics/top?from=2025-10-31T00:00:00Z&to=2025-11-07T23:59:59Z&limit=5",
          "host": ["http://localhost:8000"],
          "path": ["metrics", "top"],
          "query": [
            {"key": "from", "value": "2025-10-31T00:00:00Z"},
            {"key": "to", "value": "2025-11-07T23:59:59Z"},
            {"key": "limit", "value": "5"}
          ]
        }
      }
    },
    {
      "name": "Get Aggregate",
      "request": {
        "method": "GET",
        "url": {
          "raw": "http://localhost:8000/metrics/aggregate?from=2025-10-31T00:00:00Z&to=2025-11-07T23:59:59Z&bucket=day",
          "host": ["http://localhost:8000"],
          "path": ["metrics", "aggregate"],
          "query": [
            {"key": "from", "value": "2025-10-31T00:00:00Z"},
            {"key": "to", "value": "2025-11-07T23:59:59Z"},
            {"key": "bucket", "value": "day"}
          ]
        }
      }
    }
  ]
}
```

## 📊 Vérifier les données dans SQLite

```bash
cd /Users/alexandrupanta/Documents/crypto-viz/ingestor

# Voir toutes les tables
sqlite3 scraper/component/scraperdb/data/ingestor.db ".tables"

# Voir les symboles
sqlite3 scraper/component/scraperdb/data/ingestor.db "SELECT * FROM symbol;"

# Voir les articles (10 derniers)
sqlite3 scraper/component/scraperdb/data/ingestor.db "SELECT date, source, symbol, price FROM article ORDER BY date DESC LIMIT 10;"

# Voir les deltas
sqlite3 scraper/component/scraperdb/data/ingestor.db "SELECT symbol, date_start, delta_pct FROM delta ORDER BY date_start DESC LIMIT 10;"

# Compter les enregistrements
sqlite3 scraper/component/scraperdb/data/ingestor.db "SELECT COUNT(*) FROM article;"
```

## 🔍 Dépannage

### L'API ne démarre pas
```bash
# Vérifier les logs
uvicorn scraper.main:app --reload --log-level debug

# Vérifier que le port 8001 n'est pas utilisé
lsof -i :8001

# Insérer les données de test
python3 scraper/tools/insert_test_data.py
```

### Erreur "Module not found"
```bash
# Vérifier PYTHONPATH
export PYTHONPATH=/Users/alexandrupanta/Documents/crypto-viz/ingestor:$PYTHONPATH

# Ou réinstaller le package
cd /Users/alexandrupanta/Documents/crypto-viz/ingestor
pip install -e .
```

## 📝 Exemples de réponses attendues

### `/metrics/trending`
```json
{
  "level": "info",
  "msg": "Success",
  "response": [
    {
      "symbol": "BTC",
      "delta": 450.0,
      "delta_pct": 2.5
    }
  ]
}
```

### `/metrics/timeseries`
```json
[
  {
    "t": "2025-11-01",
    "count": 12
  },
  {
    "t": "2025-11-02",
    "count": 15
  }
]
```

### `/metrics/latest`
```json
[
  {
    "date": "2025-11-07 10:00:00",
    "source": "coindesk",
    "symbol": "BTC",
    "price": 55000.0,
    "titre": "Bitcoin reaches new high",
    "url": "https://example.com/article"
  }
]
```

### `/metrics/top`
```json
[
  {
    "source": "coindesk",
    "value": 15
  },
  {
    "source": "cointelegraph",
    "value": 12
  }
]
```

## 🎯 Tests automatisés avec pytest

Créer `tests/test_metrics.py` :

```python
import pytest
from fastapi.testclient import TestClient
from scraper.api.main import app

client = TestClient(app)

def test_get_latest():
    response = client.get("/metrics/latest")
    assert response.status_code == 200
    
def test_get_trending():
    response = client.get(
        "/metrics/trending",
        params={
            "from": "2025-10-31T00:00:00Z",
            "to": "2025-11-07T23:59:59Z",
            "bucket": "day",
            "limit": 5
        }
    )
    assert response.status_code == 200
```

Exécuter :
```bash
pytest tests/test_metrics.py -v
```
