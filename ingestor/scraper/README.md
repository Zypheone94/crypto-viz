# CryptoViz Scraper

## What is the Scraper?

The scraper is a critical component of the CryptoViz platform that collects, processes, and stores cryptocurrency data from multiple sources. It serves as the data acquisition layer of the entire system, providing fresh and relevant information for analysis and visualization.

## How Does It Work?

The scraper operates through several coordinated modules:

1. **Scheduling System**: Runs data collection at configurable intervals using Python's threading module
2. **Multiple Collection Methods**: Uses both RSS parsing and Scrapy spiders for different data types
3. **Data Processing Pipeline**: Cleans, normalizes, and enriches the raw data
4. **Configurable Data Sink**: Writes data to either filesystem (NDJSON files) or Kafka message broker (feature flag `INGEST_SINK`)
5. **API Server**: Provides health checks and data status endpoints

Each module works together to ensure a reliable and efficient data collection process:

When started, the scraper launches several processes:
- The RSS scraper runs every 5 minutes (configurable)
- The CoinGecko API scraper runs hourly (configurable)
- The prompt generator runs every 6 hours (configurable)
- A FastAPI server provides monitoring endpoints

## What Does It Collect?

This component is responsible for collecting cryptocurrency data from various sources:

1. **RSS News Scraper**: Fetches crypto news articles from CoinDesk and CoinTelegraph RSS feeds
2. **CoinGecko API Scraper**: Fetches cryptocurrency market data including prices, market cap, etc.
3. **ChatGPT Prompt Generator**: Creates analysis prompts based on cryptocurrency market data

## Features

- **Web scraping** of cryptocurrency news and price data
- **HTML content cleaning** before storing data
- **Automatic scheduling** for regular data fetching
- **FastAPI health endpoint** for monitoring
- **ChatGPT prompt generation** for financial analysis
- **Configurable data sinks** (filesystem or Kafka)

## Technical Architecture

The scraper follows a modular architecture:

```
scraperweb/
├── main.py              # Main entry point and scheduler
├── rss.py               # RSS feed parsing functionality
├── rss_scraper_poc.py   # RSS scraping implementation
├── models.py            # Data models for articles
├── models_crypto.py     # Data models for cryptocurrency data
├── sink.py              # Data sink abstraction (filesystem/Kafka)
├── io_ndjson.py         # NDJSON file I/O utilities
├── api.py               # FastAPI server endpoints
├── logging_json.py      # JSON-structured logging
├── html_utils.py        # HTML cleaning utilities
└── scrapers/            # Scrapy spiders
    ├── pipelines.py     # Data processing pipelines
    ├── run_spiders.py   # Spider runner utility
    └── spiders/         # Individual scrapers
        ├── coindesk_spider.py      # News article scraper
        └── coingecko_spider.py     # Cryptocurrency price data scraper
```

### Data Flow

1. **Collection**: RSS feeds and API endpoints are queried at regular intervals
2. **Processing**: Raw data is cleaned, normalized, and converted to structured models
3. **Storage**: Processed data is written to the configured sink (filesystem or Kafka)
4. **Analysis**: Market data is analyzed to generate prompts for further insights

## Configuration

All configuration is managed through the `.env` file. A template `.env.example` file is provided in the repository.

### Setting Up Environment Variables

Before running the scraper, you need to set up your environment variables:

1. Copy the example environment file to create your own configuration:
   ```bash
   cp scraperweb/.env.example scraperweb/.env
   ```

2. Edit the `.env` file to add your API keys and customize settings:
   ```bash
   # Add your OpenAI API key for ChatGPT prompt generation
   openai_api_key=your_key_here
   
   # Add your CoinGecko API key (optional, improves rate limits)
   COINGECKO_API_KEY=your_key_here
   ```

> **Note**: The `.env` file contains sensitive information and should never be committed to the repository. It is included in the `.gitignore` file.

### Available Configuration Options

```
# API Keys
openai_api_key=your_openai_api_key
COINGECKO_API_KEY=your_coingecko_api_key  # Optional, improves rate limits

# Server Configuration
SCRAPER_PORT=8000
HOST=0.0.0.0

# Data Configuration
DATA_PATH=./data
FETCH_INTERVAL=300             # RSS fetch interval in seconds (default: 5 min)
CRYPTO_FETCH_INTERVAL=3600     # CoinGecko API fetch interval in seconds (default: 1 hour)
PROMPT_GEN_INTERVAL=21600      # ChatGPT prompt generation interval in seconds (default: 6 hours)

# Force write even if articles already exist (for testing)
FORCE_WRITE=true

# Sources Configuration
SOURCES=coindesk,cointelegraph

# RSS Feed URLs
COINDESK_RSS_URL=https://www.coindesk.com/arc/outboundfeeds/rss/
COINTELEGRAPH_RSS_URL=https://cointelegraph.com/rss
```

## Data Structure

### Cryptocurrency Price Data

The CoinGecko spider collects cryptocurrency price data with the following structure:

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

### ChatGPT Prompts

The prompt generator creates two files for each prompt:
- `crypto_analysis_YYYYMMDD_HHMMSS.json` - Full prompt data with metadata
- `crypto_analysis_YYYYMMDD_HHMMSS.txt` - Plain text prompt for easy copying

Example JSON structure:
```json
{
  "prompt_id": "crypto_analysis_20230615_1200",
  "timestamp": "2023-06-15T12:00:00Z",
  "top_coins": [...],
  "prompt_text": "As a cryptocurrency financial analyst..."
}
```

## Usage

### Running the Scraper

```bash
cd ingestor/scraper
# Run the scraper
python -m scraperweb.main
```

For Windows users:
```powershell
cd C:\path\to\crypto-viz\ingestor\scraper
python -m scraperweb.main
```

### Running Individual Components

You can run specific components separately:

```bash
# Run only RSS scraper
python -m scraperweb.rss_scraper_poc

# Run Scrapy spiders directly
python -m scraperweb.scrapers.run_spiders

# Run just the API server
python -m scraperweb.api
```

### Accessing the API

The scraper includes a FastAPI server with a health endpoint:

```
GET http://localhost:8000/health
```

Additional endpoints:
```
GET http://localhost:8000/metrics - Basic metrics about collected data
GET http://localhost:8000/status - Detailed system status
```

### Generated Prompts

ChatGPT prompts are saved to the `data/prompts` directory and can be used for financial analysis with OpenAI's API or by copying the `.txt` file content directly into ChatGPT.

## Development Guide

### Project Structure

```
scraperweb/
├── main.py              # Main entry point and scheduler
├── rss.py               # RSS feed parsing functionality
├── sink.py              # Data sink abstraction (filesystem/Kafka)
├── api.py               # FastAPI server endpoints
├── scrapers/            # Scrapy spiders
    └── spiders/         # Individual scrapers
```

### Adding a New Data Source

To add a new data source:

1. **For RSS sources**:
   - Add the RSS URL to the environment variables
   - Update the `rss.py` module to include the new source

2. **For web scraping**:
   - Create a new Scrapy spider in `scrapers/spiders/`
   - Implement the parsing logic for the new source
   - Register the spider in `run_spiders.py`

### Extending the Data Sink

To add a new data sink type:

1. Create a new class in `sink.py` that implements the same interface as `KafkaSink`
2. Update the `write_to_sink` function to handle the new sink type
3. Add appropriate environment variable handling

### Testing

Run tests with:

```bash
pytest tests/
```

Key test files:
- `tests/test_rss.py` - Tests for RSS functionality
- `tests/test_sink.py` - Tests for sink functionality

## Configuring the Data Sink (CRY-19)

The scraper supports multiple data sinks through the `INGEST_SINK` feature flag:

### Filesystem Sink (Default)

Data is written to NDJSON files in the `data/raw/YYYY/MM/DD/` directory structure. Files are organized by date and source with proper timestamping.

```
INGEST_SINK=filesystem
```

The filesystem sink offers:
- Simple storage without external dependencies
- Clear directory structure for data organization
- Human-readable NDJSON files for easy inspection
- Automatic date-based partitioning

### Kafka Sink

Data can be streamed to Kafka for real-time processing, enabling integration with streaming data pipelines:

```
INGEST_SINK=kafka
KAFKA_BOOTSTRAP=localhost:9094
KAFKA_TOPIC=news.raw
KAFKA_SECURITY_PROTOCOL=PLAINTEXT
KAFKA_RETRIES=5
KAFKA_RETRY_BACKOFF_MS=500
KAFKA_MAX_IN_FLIGHT=5
```

The Kafka sink provides:
- Real-time data streaming capabilities
- Automatic topic creation (if not exists)
- Fault tolerance with configurable retries
- Message deduplication using SHA-1 keys
- Automatic fallback to filesystem if Kafka is unavailable

### Implementation Details

The sink functionality is implemented in `scraperweb/sink.py` with these key components:

1. **Feature Flag Detection**: Reads the `INGEST_SINK` environment variable
2. **Dynamic Loading**: Checks for kafka-python library availability
3. **Unified API**: Common interface for both sink types
4. **Graceful Fallback**: Falls back to filesystem if Kafka fails
5. **Type Safety**: Full typing support with Pydantic models

### Switching Between Sinks

To change the data sink, update the `INGEST_SINK` environment variable:

```bash
# When running directly
INGEST_SINK=kafka python -m scraperweb.main

# Or in docker-compose.yml
environment:
  - INGEST_SINK=kafka
```

### Troubleshooting

If using Kafka sink:
- Ensure kafka-python is installed: `pip install kafka-python`
- Verify Kafka broker is accessible at the configured bootstrap servers
- Check Kafka topic permissions if seeing authorization errors
- Monitor logs for connection issues or serialization errors