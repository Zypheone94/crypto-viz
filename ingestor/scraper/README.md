# CryptoViz Scraper

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

### Accessing the API

The scraper includes a FastAPI server with a health endpoint:

```
GET http://localhost:8000/health
```

### Generated Prompts

ChatGPT prompts are saved to the `data/prompts` directory and can be used for financial analysis with OpenAI's API or by copying the `.txt` file content directly into ChatGPT.