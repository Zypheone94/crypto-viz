from scrapy import Spider, Request
from datetime import datetime, timezone
import json
import sys
from pathlib import Path

# Add parent directory to path to import models
sys.path.append(str(Path(__file__).parent.parent.parent))

class CoinGeckoSpider(Spider):
    name = 'coingecko'
    allowed_domains = ['api.coingecko.com']
    start_urls = [
        'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=100&page=1',
        'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=100&page=2'
    ]
    
    custom_settings = {
        'USER_AGENT': 'crypto-viz-scraper/1.0',
        'ROBOTSTXT_OBEY': False,
        'DOWNLOAD_DELAY': 1,
        'CONCURRENT_REQUESTS': 1,
        'RANDOMIZE_DOWNLOAD_DELAY': 0.5
    }

    async def start(self):
        for url in self.start_urls:
            yield Request(url, callback=self.parse_crypto_data, meta={'source': 'coingecko_api'})

    def parse_crypto_data(self, response):
        try:
            data = json.loads(response.text)
            now_utc = datetime.now(timezone.utc)
            
            for coin in data:
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
                    'fetched_at': now_utc.isoformat(),
                    'published_at': now_utc.isoformat()
                }
                # ⚡ Log every scraped coin
                self.logger.info(f"Scraped CoinGecko coin: {crypto_data['name']}")
                yield crypto_data

        except Exception as e:
            self.logger.error(f'Error parsing CoinGecko API data: {e}')
            yield {
                'id': f"coingecko_error_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                'source': 'coingecko',
                'type': 'error',
                'error': str(e),
                'fetched_at': datetime.now(timezone.utc).isoformat(),
                'published_at': datetime.now(timezone.utc).isoformat()
            }
