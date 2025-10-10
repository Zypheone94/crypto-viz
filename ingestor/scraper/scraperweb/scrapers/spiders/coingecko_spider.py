from scrapy import Spider, Request
from datetime import datetime, timezone
import json
import sys
import os
import logging
from pathlib import Path

# Add parent directory to path to import models
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from scraperweb.models_crypto import CryptoPriceModel

# Set up basic logging for debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
)
logger = logging.getLogger('coingecko_spider')

class CoinGeckoSpider(Spider):
    name = 'coingecko'
    allowed_domains = ['api.coingecko.com', 'www.coingecko.com']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Get API key from environment
        self.api_key = os.getenv('COINGECKO_API_KEY', '')
        logger.info(f"CoinGecko API Key configured: {'Yes' if self.api_key else 'No (will use free tier API)'}")
        
        # Set up URLs with API key if available
        # CoinGecko API v3 for market data
        base_url = 'https://api.coingecko.com/api/v3/coins/markets'
        params = 'vs_currency=usd&order=market_cap_desc&per_page=100&sparkline=false&price_change_percentage=24h'
        
        # Add API key if available
        api_header = {}
        if self.api_key:
            # Using header-based auth for API v3
            api_header['x-cg-api-key'] = self.api_key
        
        # Store URLs
        self.urls = [
            f'{base_url}?{params}&page=1',
            f'{base_url}?{params}&page=2'
        ]
        
        # Store headers
        self.api_headers = api_header
        logger.info(f"Starting CoinGecko spider with URLs: {[url.split('?')[0] + '?...' for url in self.urls]}")
        logger.info(f"Data directory: {os.getenv('DATA_PATH', './data')}")
    
    custom_settings = {
        'USER_AGENT': 'crypto-viz-scraper/1.0 (+https://github.com/user/crypto-viz)',
        'ROBOTSTXT_OBEY': False,
        'DOWNLOAD_DELAY': 5,  # Increased to respect rate limits
        'CONCURRENT_REQUESTS': 1,
        'RANDOMIZE_DOWNLOAD_DELAY': 1.0,
        'RETRY_TIMES': 3,
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429],
        'HTTPCACHE_ENABLED': True,
        'HTTPCACHE_EXPIRATION_SECS': 300,
        'ITEM_PIPELINES': {
            'scraperweb.scrapers.pipelines.CryptoDataPipeline': 300,
        },
    }

    def start_requests(self):
        # Log that we're starting requests
        logger.info("Starting CoinGecko requests")
        
        # Make requests with proper headers
        for url in self.urls:
            logger.info(f"Making request to {url}")
            yield Request(
                url=url, 
                callback=self.parse_crypto_data, 
                meta={'source': 'coingecko_api'},
                errback=self.errback_http,
                headers=self.api_headers,
                priority=10  # High priority
            )

    def parse_crypto_data(self, response):
        try:
            logger.info(f"Received response from {response.url}")
            logger.info(f"Response status: {response.status}")
            
            # Parse JSON response
            try:
                data = json.loads(response.text)
            except json.JSONDecodeError as jde:
                # Handle invalid JSON - log the first part of the response
                logger.error(f"JSON decode error: {jde}")
                logger.error(f"Response: {response.text[:500]}...")
                yield self._create_error_item(f"JSON decode error: {str(jde)}", datetime.now(timezone.utc))
                return
                
            now_utc = datetime.now(timezone.utc)
            
            # Check if response is valid
            if not isinstance(data, list):
                logger.error(f"Invalid response format: {type(data)}")
                if isinstance(data, dict):
                    logger.error(f"API Error: {json.dumps(data, indent=2)[:500]}")
                    # Check for rate limiting
                    if 'status' in data and data.get('status', {}).get('error_code', 0) == 429:
                        logger.error("RATE LIMITED - Consider getting a CoinGecko API key")
                yield self._create_error_item("Invalid response format", now_utc)
                return
                
            logger.info(f"Processing {len(data)} coins from CoinGecko")
            
            for coin in data:
                try:
                    # Extract all available data
                    crypto_data = {
                        'id': f"coingecko_{coin['id']}_{now_utc.strftime('%Y%m%d_%H%M')}",
                        'source': 'coingecko',
                        'type': 'crypto_price',
                        'name': coin['name'],
                        'symbol': coin['symbol'].upper(),
                        'current_price': coin.get('current_price'),
                        'market_cap': coin.get('market_cap'),
                        'market_cap_rank': coin.get('market_cap_rank'),
                        'total_volume': coin.get('total_volume'),
                        'price_change_24h': coin.get('price_change_24h'),
                        'price_change_percentage_24h': coin.get('price_change_percentage_24h'),
                        'high_24h': coin.get('high_24h'),
                        'low_24h': coin.get('low_24h'),
                        'circulating_supply': coin.get('circulating_supply'),
                        'total_supply': coin.get('total_supply'),
                        'max_supply': coin.get('max_supply'),
                        'fetched_at': now_utc.isoformat(),
                        'published_at': now_utc.isoformat()
                    }
                    
                    # Validate with our model
                    validated_data = CryptoPriceModel(**crypto_data).dict()
                    
                    # Log progress
                    if coin.get('market_cap_rank', 0) <= 20:
                        self.logger.info(f"Scraped #{coin.get('market_cap_rank', 'N/A')} {crypto_data['name']} ({crypto_data['symbol']}): ${crypto_data['current_price']:,.2f}")
                    
                    yield validated_data
                except Exception as coin_error:
                    self.logger.error(f"Error processing coin {coin.get('id', 'unknown')}: {coin_error}")
                    # Continue processing other coins
            
            # Log completion
            self.logger.info(f"Completed processing page from {response.url}")

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}")
            self.logger.error(f"Response text: {response.text[:200]}...")  # Log first 200 chars
            yield self._create_error_item(f"JSON decode error: {str(e)}", now_utc)
        except Exception as e:
            self.logger.error(f"Error parsing CoinGecko API data: {e}")
            yield self._create_error_item(str(e), datetime.now(timezone.utc))

    def errback_http(self, failure):
        """Handle failed requests"""
        self.logger.error(f"Request failed: {failure.value}")
        yield self._create_error_item(f"Request failed: {failure.value}", datetime.now(timezone.utc))
    
    def _create_error_item(self, error_msg, timestamp):
        """Helper to create error items"""
        return {
            'id': f"coingecko_error_{timestamp.strftime('%Y%m%d_%H%M%S')}",
            'source': 'coingecko',
            'type': 'error',
            'error': str(error_msg),
            'fetched_at': timestamp.isoformat(),
            'published_at': timestamp.isoformat()
        }
