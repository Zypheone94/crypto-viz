from scrapy import Spider, Request
from datetime import datetime, timezone
import json
import sys
import os
import logging
import re
from pathlib import Path

# Add parent directory to path to import models
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from scraperweb.models_crypto import CryptoPriceModel

# Set up basic logging for debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
)
logger = logging.getLogger('coindesk_price_spider')

class CoinDeskPriceSpider(Spider):
    name = 'coindesk_price'
    allowed_domains = ['www.coindesk.com']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # CoinDesk price page URL
        self.start_urls = ['https://www.coindesk.com/price']
        
        logger.info("Starting CoinDesk price spider")
        logger.info(f"Target URL: {self.start_urls[0]}")
        logger.info(f"Data directory: {os.getenv('DATA_PATH', './data')}")
    
    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'ROBOTSTXT_OBEY': False,
        'DOWNLOAD_DELAY': 3,
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
        """Generate initial requests"""
        logger.info("Starting CoinDesk price requests")
        
        for url in self.start_urls:
            logger.info(f"Making request to {url}")
            yield Request(
                url=url, 
                callback=self.parse_price_data, 
                meta={'source': 'coindesk_price'},
                errback=self.errback_http,
                headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                },
                priority=10
            )

    def parse_price_data(self, response):
        """Parse the CoinDesk price page"""
        try:
            logger.info(f"Received response from {response.url}")
            logger.info(f"Response status: {response.status}")
            
            now_utc = datetime.now(timezone.utc)
            
            # Look for price data in the HTML
            # CoinDesk price page often contains data in script tags or data attributes
            
            # Method 1: Try to find JSON data in script tags
            script_data = self._extract_json_from_scripts(response)
            if script_data:
                yield from self._process_json_data(script_data, now_utc)
                return
            
            # Method 2: Try to parse HTML table/div structure
            html_data = self._extract_data_from_html(response)
            if html_data:
                yield from self._process_html_data(html_data, now_utc)
                return
            
            # Method 3: Look for specific CSS selectors commonly used for crypto prices
            selector_data = self._extract_data_from_selectors(response)
            if selector_data:
                yield from self._process_selector_data(selector_data, now_utc)
                return
            
            logger.warning("No crypto price data found on the page")
            yield self._create_error_item("No price data found", now_utc)
            
        except Exception as e:
            logger.error(f"Error parsing CoinDesk price data: {e}")
            yield self._create_error_item(str(e), datetime.now(timezone.utc))

    def _extract_json_from_scripts(self, response):
        """Extract JSON data from script tags"""
        try:
            # Look for script tags that might contain price data
            scripts = response.css('script::text').getall()
            
            for script in scripts:
                # Look for common patterns that might contain crypto data
                if any(keyword in script.lower() for keyword in ['price', 'crypto', 'coin', 'market', 'bitcoin']):
                    # Try to extract JSON objects
                    json_matches = re.findall(r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})', script)
                    for match in json_matches:
                        try:
                            data = json.loads(match)
                            if self._is_crypto_data(data):
                                return data
                        except json.JSONDecodeError:
                            continue
            
            return None
        except Exception as e:
            logger.error(f"Error extracting JSON from scripts: {e}")
            return None

    def _extract_data_from_html(self, response):
        """Extract data from HTML structure"""
        try:
            crypto_data = []
            
            # Look for common table structures
            rows = response.css('table tr, .price-table tr, .crypto-table tr')
            
            for row in rows:
                # Extract cryptocurrency information from table rows
                name_element = row.css('.name, .coin-name, .currency-name, td:first-child ::text').get()
                symbol_element = row.css('.symbol, .coin-symbol, .ticker ::text').get()
                price_element = row.css('.price, .current-price, .value ::text').get()
                
                if name_element and price_element:
                    # Clean up the extracted data
                    name = name_element.strip()
                    price_text = price_element.strip().replace('$', '').replace(',', '')
                    
                    try:
                        price = float(price_text)
                        crypto_data.append({
                            'name': name,
                            'symbol': symbol_element.strip() if symbol_element else name[:3].upper(),
                            'price': price
                        })
                    except ValueError:
                        continue
            
            return crypto_data if crypto_data else None
            
        except Exception as e:
            logger.error(f"Error extracting data from HTML: {e}")
            return None

    def _extract_data_from_selectors(self, response):
        """Extract data using specific CSS selectors"""
        try:
            crypto_data = []
            
            # Common selectors for crypto price data
            selectors = [
                '.price-item, .crypto-item, .coin-item',
                '[data-currency], [data-coin], [data-symbol]',
                '.price-row, .crypto-row, .coin-row'
            ]
            
            for selector in selectors:
                elements = response.css(selector)
                if elements:
                    for element in elements:
                        data = self._extract_single_crypto_data(element)
                        if data:
                            crypto_data.append(data)
                    break
            
            return crypto_data if crypto_data else None
            
        except Exception as e:
            logger.error(f"Error extracting data from selectors: {e}")
            return None

    def _extract_single_crypto_data(self, element):
        """Extract crypto data from a single HTML element"""
        try:
            # Try various ways to extract name, symbol, and price
            name = (
                element.css('.name ::text').get() or
                element.css('[data-name] ::text').get() or
                element.attrib.get('data-name') or
                element.css('::text').re_first(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)')
            )
            
            symbol = (
                element.css('.symbol ::text').get() or
                element.css('[data-symbol] ::text').get() or
                element.attrib.get('data-symbol') or
                element.css('::text').re_first(r'\b([A-Z]{2,5})\b')
            )
            
            price_text = (
                element.css('.price ::text').get() or
                element.css('[data-price] ::text').get() or
                element.attrib.get('data-price') or
                element.css('::text').re_first(r'\$?([\d,]+\.?\d*)')
            )
            
            if name and price_text:
                price = float(price_text.replace('$', '').replace(',', ''))
                return {
                    'name': name.strip(),
                    'symbol': symbol.strip() if symbol else name[:3].upper(),
                    'price': price
                }
            
            return None
            
        except Exception as e:
            logger.debug(f"Error extracting single crypto data: {e}")
            return None

    def _is_crypto_data(self, data):
        """Check if JSON data contains cryptocurrency information"""
        if not isinstance(data, dict):
            return False
        
        # Look for common cryptocurrency data fields
        crypto_fields = ['price', 'symbol', 'name', 'currency', 'coin', 'crypto']
        return any(field in str(data).lower() for field in crypto_fields)

    def _process_json_data(self, data, timestamp):
        """Process extracted JSON data"""
        try:
            # Handle different JSON structures
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                # Look for arrays within the object
                items = []
                for value in data.values():
                    if isinstance(value, list):
                        items.extend(value)
                    elif isinstance(value, dict) and self._is_crypto_data(value):
                        items.append(value)
            else:
                return
            
            for item in items:
                if isinstance(item, dict) and self._is_crypto_data(item):
                    crypto_item = self._create_crypto_item(item, timestamp)
                    if crypto_item:
                        yield crypto_item
                        
        except Exception as e:
            logger.error(f"Error processing JSON data: {e}")

    def _process_html_data(self, data, timestamp):
        """Process extracted HTML data"""
        try:
            for item in data:
                crypto_item = self._create_crypto_item(item, timestamp)
                if crypto_item:
                    yield crypto_item
                    
        except Exception as e:
            logger.error(f"Error processing HTML data: {e}")

    def _process_selector_data(self, data, timestamp):
        """Process extracted selector data"""
        try:
            for item in data:
                crypto_item = self._create_crypto_item(item, timestamp)
                if crypto_item:
                    yield crypto_item
                    
        except Exception as e:
            logger.error(f"Error processing selector data: {e}")

    def _create_crypto_item(self, raw_data, timestamp):
        """Create a standardized crypto item from raw data"""
        try:
            # Extract basic information
            name = raw_data.get('name', '').strip()
            symbol = raw_data.get('symbol', '').strip().upper()
            price = raw_data.get('price', raw_data.get('current_price', 0))
            
            # Skip if essential data is missing
            if not name or not price:
                return None
            
            # Create standardized crypto data
            crypto_data = {
                'id': f"coindesk_{symbol.lower()}_{timestamp.strftime('%Y%m%d_%H%M')}",
                'source': 'coindesk_price',
                'type': 'crypto_price',
                'name': name,
                'symbol': symbol,
                'current_price': float(price),
                'market_cap': raw_data.get('market_cap'),
                'market_cap_rank': raw_data.get('rank'),
                'total_volume': raw_data.get('volume'),
                'price_change_24h': raw_data.get('change_24h'),
                'price_change_percentage_24h': raw_data.get('change_percentage_24h'),
                'high_24h': raw_data.get('high_24h'),
                'low_24h': raw_data.get('low_24h'),
                'circulating_supply': raw_data.get('circulating_supply'),
                'total_supply': raw_data.get('total_supply'),
                'max_supply': raw_data.get('max_supply'),
                'fetched_at': timestamp.isoformat(),
                'published_at': timestamp.isoformat()
            }
            
            # Validate with our model
            validated_data = CryptoPriceModel(**crypto_data).dict()
            
            # Log progress for major cryptocurrencies
            logger.info(f"Scraped {name} ({symbol}): ${price:,.2f}")
            
            return validated_data
            
        except Exception as e:
            logger.error(f"Error creating crypto item: {e}")
            return None

    def errback_http(self, failure):
        """Handle failed requests"""
        logger.error(f"Request failed: {failure.value}")
        yield self._create_error_item(f"Request failed: {failure.value}", datetime.now(timezone.utc))
    
    def _create_error_item(self, error_msg, timestamp):
        """Helper to create error items"""
        return {
            'id': f"coindesk_price_error_{timestamp.strftime('%Y%m%d_%H%M%S')}",
            'source': 'coindesk_price',
            'type': 'error',
            'error': str(error_msg),
            'fetched_at': timestamp.isoformat(),
            'published_at': timestamp.isoformat()
        }