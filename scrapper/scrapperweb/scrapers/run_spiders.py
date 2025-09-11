from scrapy.crawler import CrawlerRunner
from scrapy.utils.log import configure_logging
from scrapy.utils.project import get_project_settings
from scrapers.spiders.coindesk_spider import CoinDeskSpider
from scrapers.spiders.coingecko_spider import CoinGeckoSpider
from twisted.internet import reactor
import os
from datetime import datetime

def setup_crawler(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    settings = get_project_settings()
    settings.update({
        'FEEDS': {
            os.path.join(output_dir, f'coindesk_{timestamp}.json'): {
                'format': 'json',
                'encoding': 'utf8',
                'indent': 2,
                'overwrite': True
            },
            os.path.join(output_dir, f'coingecko_{timestamp}.json'): {
                'format': 'json',
                'encoding': 'utf8',
                'indent': 2,
                'overwrite': True
            }
        },
        'LOG_LEVEL': 'INFO',
        'ROBOTSTXT_OBEY': True,
        'CONCURRENT_REQUESTS': 1,
        'DOWNLOAD_DELAY': 2,
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    
    configure_logging()
    return CrawlerRunner(settings)
