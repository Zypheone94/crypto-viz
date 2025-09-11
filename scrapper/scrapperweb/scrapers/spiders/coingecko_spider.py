from scrapy import Spider
from datetime import datetime
import requests

class CoinGeckoSpider(Spider):
    name = 'coingecko'
    allowed_domains = ['api.coingecko.com']
    start_urls = ['https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=20&page=1']
    
    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'ROBOTSTXT_OBEY': True,
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS': 1
    }

    def parse(self, response):
        try:
            # Use requests directly to get API data
            resp = requests.get(self.start_urls[0])
            resp.raise_for_status()
            data = resp.json()
            
            for coin in data:
                yield {
                    'source': 'coingecko',
                    'name': coin['name'],
                    'symbol': coin['symbol'].upper(),
                    'price': f"${coin['current_price']:,.2f}",
                    'market_cap': f"${coin['market_cap']:,.0f}",
                    '24h_change': f"{coin['price_change_percentage_24h']:.2f}%",
                    'scrape_timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            self.logger.error(f'Error fetching CoinGecko API data: {e}')
