from scrapy.crawler import CrawlerRunner
from scrapy.utils.log import configure_logging
from scrapy.utils.project import get_project_settings
from scrapers.spiders.coindesk_spider import CoinDeskSpider
from scrapers.spiders.coingecko_spider import CoinGeckoSpider
from twisted.internet import defer, asyncioreactor
import os
from pathlib import Path

# Install Twisted asyncio reactor for compatibility with FastAPI
try:
    asyncioreactor.install()
except Exception:
    pass  # Reactor may already be installed

def setup_crawler(output_dir: str) -> CrawlerRunner:
    """Setup a Scrapy CrawlerRunner with proper settings."""
    os.makedirs(output_dir, exist_ok=True)
    raw_dir = Path(output_dir) / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    settings = get_project_settings()
    settings.update({
        'LOG_LEVEL': 'INFO',
        'ROBOTSTXT_OBEY': True,
        'CONCURRENT_REQUESTS': 1,
        'DOWNLOAD_DELAY': 1,
        'RANDOMIZE_DOWNLOAD_DELAY': 0.5,
        'USER_AGENT': 'crypto-viz-scraper/1.0',
        'RETRY_TIMES': 3,
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429],
        'HTTPCACHE_ENABLED': True,
        'HTTPCACHE_EXPIRATION_SECS': 300,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 1,
        'AUTOTHROTTLE_MAX_DELAY': 10,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 1.0,
        'COOKIES_ENABLED': False,
        'TELNETCONSOLE_ENABLED': False,
        'ITEM_PIPELINES': {
            'scrapers.pipelines.CryptoDataPipeline': 300,
        },
    })

    configure_logging()
    return CrawlerRunner(settings)


async def run_spiders(runner: CrawlerRunner):
    """Run CoinDesk and CoinGecko spiders asynchronously."""
    d1 = runner.crawl(CoinDeskSpider)
    d2 = runner.crawl(CoinGeckoSpider)
    # Wait for both crawls to finish
    await defer.DeferredList([d1, d2])
