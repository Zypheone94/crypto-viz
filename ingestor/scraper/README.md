# CryptoViz Scraper

## Qu’est-ce que le Scraper ?

Le scraper est un composant essentiel de la plateforme CryptoViz qui collecte, traite et stocke les données liées aux cryptomonnaies à partir de multiples sources. Il sert de couche d’acquisition de données pour l’ensemble du système, fournissant des informations fraîches et pertinentes pour l’analyse et la visualisation.

## Comment fonctionne-t-il ?

Le scraper fonctionne à travers plusieurs modules coordonnés :

1. **Système de planification** : exécute la collecte de données à des intervalles configurables à l’aide du module `threading` de Python
2. **Méthodes de collecte multiples** : utilise à la fois l’analyse de flux RSS et des spiders Scrapy pour différents types de données
3. **Pipeline de traitement des données** : nettoie, normalise et enrichit les données brutes
4. **Système de stockage configurable** : enregistre les données soit dans le système de fichiers (fichiers NDJSON), soit dans un broker Kafka (feature flag `INGEST_SINK`)
5. **Serveur API** : fournit des endpoints pour les checks de santé et l’état des données

Chaque module fonctionne ensemble pour garantir un processus de collecte fiable et efficace :

Au démarrage, le scraper lance plusieurs processus :

* Le scraper RSS s’exécute toutes les 5 minutes (configurable)
* Le scraper d’API CoinGecko s’exécute toutes les heures (configurable)
* Le générateur de prompts s’exécute toutes les 6 heures (configurable)
* Un serveur FastAPI fournit des endpoints de monitoring

## Que collecte-t-il ?

Ce composant est chargé de collecter des données liées aux cryptomonnaies à partir de diverses sources :

1. **Scraper d’actualités RSS** : récupère des articles d’actualité crypto depuis les flux RSS de CoinDesk et CoinTelegraph
2. **Scraper de l’API CoinGecko** : collecte des données de marché (prix, capitalisation, etc.)
3. **Générateur de prompts ChatGPT** : crée des prompts d’analyse basés sur les données du marché crypto

## Fonctionnalités

* **Web scraping** des actualités et des données de prix
* **Nettoyage du contenu HTML** avant stockage
* **Planification automatique** de la récupération des données
* **Endpoint de santé FastAPI** pour le monitoring
* **Génération de prompts ChatGPT** pour l’analyse financière
* **Systèmes de stockage configurables** (filesystem ou Kafka)

## Architecture technique

Le scraper suit une architecture modulaire :

```
scraperweb/
├── main.py              # Point d’entrée principal et scheduler
├── rss.py               # Fonctionnalité d’analyse RSS
├── rss_scraper_poc.py   # Implémentation du scraping RSS
├── models.py            # Modèles de données pour les articles
├── models_crypto.py     # Modèles de données pour les cryptomonnaies
├── sink.py              # Abstraction du data sink (filesystem/Kafka)
├── io_ndjson.py         # Utilitaires d’E/S NDJSON
├── api.py               # Endpoints FastAPI
├── logging_json.py      # Logs structurés en JSON
├── html_utils.py        # Utilitaires de nettoyage HTML
└── scrapers/            # Spiders Scrapy
    ├── pipelines.py     # Pipelines de traitement des données
    ├── run_spiders.py   # Utilitaire d’exécution des spiders
    └── spiders/         # Scrapers individuels
        ├── coindesk_spider.py      # Scraper d’articles d’actualité
        └── coingecko_spider.py     # Scraper de données de prix crypto
```

### Flux de données

1. **Collecte** : les flux RSS et endpoints API sont interrogés à intervalles réguliers
2. **Traitement** : les données brutes sont nettoyées, normalisées et converties en modèles structurés
3. **Stockage** : les données traitées sont écrites dans le sink configuré (filesystem ou Kafka)
4. **Analyse** : les données du marché sont analysées pour générer des prompts

## Configuration

Toute la configuration est gérée via le fichier `.env`. Un fichier modèle `.env.example` est fourni dans le dépôt.

### Configuration des variables d’environnement

Avant d’exécuter le scraper, configurez vos variables d’environnement :

1. Copiez le fichier d’exemple pour créer votre propre configuration :

```bash
cp scraperweb/.env.example scraperweb/.env
```

2. Modifiez le fichier `.env` pour ajouter vos clés API et personnaliser les réglages :

```bash
# Ajoutez votre clé API OpenAI pour la génération de prompts ChatGPT
openai_api_key=votre_cle_ici

# Ajoutez votre clé API CoinGecko (optionnelle, améliore les limites de taux)
COINGECKO_API_KEY=votre_cle_ici
```

> **Note** : Le fichier `.env` contient des informations sensibles et ne doit jamais être commité dans le dépôt. Il est inclus dans le `.gitignore`.

### Options de configuration disponibles

```
# Clés API
openai_api_key=votre_cle_openai
COINGECKO_API_KEY=votre_cle_coingecko  # Optionnel, améliore les limites

# Configuration du serveur
SCRAPER_PORT=8000
HOST=0.0.0.0

# Configuration des données
DATA_PATH=./data
FETCH_INTERVAL=300             # Intervalle RSS en secondes (par défaut : 5 min)
CRYPTO_FETCH_INTERVAL=3600     # Intervalle CoinGecko (par défaut : 1 heure)
PROMPT_GEN_INTERVAL=21600      # Génération de prompts (par défaut : 6h)

# Forcer l’écriture même si des articles existent (tests)
FORCE_WRITE=true

# Configuration des sources
SOURCES=coindesk,cointelegraph

# URLs RSS
COINDESK_RSS_URL=https://www.coindesk.com/arc/outboundfeeds/rss/
COINTELEGRAPH_RSS_URL=https://cointelegraph.com/rss
```

## Structure des données

### Données de prix des cryptomonnaies

Le spider CoinGecko collecte des données structurées comme suit :

```json
{
  "id": "coingecko_bitcoin_20230615_1200",
  "source": "coingecko",
  "type": "crypto_price",
  "name": "Bitcoin",
  "symbol": "BTC",
  "current_price": 35000.0,
  "market_cap": 680000000000,
  "market_cap_rank": 1,
  "total_volume": 18000000000,
  "price_change_24h": 500.0,
  "price_change_percentage_24h": 1.45,
  "high_24h": 35500.0,
  "low_24h": 34200.0,
  "circulating_supply": 19000000.0,
  "total_supply": 21000000.0,
  "max_supply": 21000000.0,
  "fetched_at": "2023-06-15T12:00:00Z",
  "published_at": "2023-06-15T12:00:00Z"
}
```

### Prompts ChatGPT

Le générateur de prompts crée deux fichiers pour chaque prompt :

* `crypto_analysis_YYYYMMDD_HHMMSS.json` – données complètes avec métadonnées
* `crypto_analysis_YYYYMMDD_HHMMSS.txt` – prompt en texte brut pour copie rapide

Exemple JSON :

```json
{
  "prompt_id": "crypto_analysis_20230615_1200",
  "timestamp": "2023-06-15T12:00:00Z",
  "top_coins": [...],
  "prompt_text": "En tant qu'analyste financier spécialisé en cryptomonnaies..."
}
```

## Utilisation

### Exécution du scraper

```bash
cd ingestor/scraper
python -m scraperweb.main
```

Sous Windows :

```powershell
cd C:\path\to\crypto-viz\ingestor\scraper
python -m scraperweb.main
```

### Exécution de composants spécifiques

```bash
# Scraper RSS uniquement
python -m scraperweb.rss_scraper_poc

# Exécuter les spiders Scrapy
python -m scraperweb.scrapers.run_spiders

# Lancer uniquement le serveur API
python -m scraperweb.api
```

### Accès à l’API

Le scraper inclut un serveur FastAPI avec un endpoint de santé :

```
GET http://localhost:8000/health
```

Autres endpoints :

```
GET http://localhost:8000/metrics - Statistiques basiques
GET http://localhost:8000/status - État détaillé du système
```

### Prompts générés

Les prompts ChatGPT sont sauvegardés dans le dossier `data/prompts` et peuvent être utilisés via l’API OpenAI ou en copiant directement le contenu du fichier `.txt`.

## Guide de développement

### Structure du projet

```
scraperweb/
├── main.py              # Point d’entrée et scheduler
├── rss.py               # Parsing RSS
├── sink.py              # Abstraction du data sink
├── api.py               # Endpoints FastAPI
├── scrapers/            # Spiders Scrapy
    └── spiders/         # Scrapers individuels
```

### Ajouter une nouvelle source de données

1. **Pour des sources RSS** :

   * Ajouter l’URL RSS dans les variables d’environnement
   * Mettre à jour le module `rss.py`

2. **Pour le scraping web** :

   * Créer un nouveau spider dans `scrapers/spiders/`
   * Implémenter la logique de parsing
   * L’enregistrer dans `run_spiders.py`

### Étendre le Data Sink

1. Créer une nouvelle classe dans `sink.py` basée sur l’interface existante
2. Mettre à jour `write_to_sink` pour supporter ce type
3. Ajouter la gestion dans les variables d’environnement

### Tests

Lancer les tests avec :

```bash
pytest tests/
```

Fichiers clés :

* `tests/test_rss.py` – Tests des fonctions RSS
* `tests/test_sink.py` – Tests des sinks

## Configuration du Data Sink (CRY-19)

Le scraper prend en charge plusieurs sinks via le feature flag `INGEST_SINK` :

### Sink Filesystem (par défaut)

Les données sont enregistrées en NDJSON dans `data/raw/YYYY/MM/DD/`.

```
INGEST_SINK=filesystem
```

Avantages :

* Pas de dépendances externes
* Structure claire par date
* Fichiers lisibles et inspectables
* Partitionnement automatique par date

### Sink Kafka

Les données peuvent être diffusées en temps réel via Kafka :

```
INGEST_SINK=kafka
KAFKA_BOOTSTRAP=localhost:9094
KAFKA_TOPIC=news.raw
KAFKA_SECURITY_PROTOCOL=PLAINTEXT
KAFKA_RETRIES=5
KAFKA_RETRY_BACKOFF_MS=500
KAFKA_MAX_IN_FLIGHT=5
```

Avantages :

* Streaming en temps réel
* Création automatique des topics
* Tolérance aux pannes avec retries
* Déduplication via clés SHA-1
* Fallback automatique vers filesystem

### Détails d’implémentation

Situé dans `scraperweb/sink.py` avec :

1. **Détection de feature flag** (`INGEST_SINK`)
2. **Chargement dynamique** (librairie kafka-python)
3. **API unifiée** pour tous les sinks
4. **Fallback automatique**
5. **Typing strict avec Pydantic**

### Changer de sink

Modifiez `INGEST_SINK` :

```bash
# En exécution directe
INGEST_SINK=kafka python -m scraperweb.main

# Ou dans docker-compose.yml
environment:
  - INGEST_SINK=kafka
```

### Dépannage

Pour Kafka :

* Vérifiez l’installation de kafka-python : `pip install kafka-python`
* Assurez-vous que le broker Kafka est accessible
* Vérifiez les permissions du topic
* Consultez les logs pour les erreurs réseau ou sérialisation