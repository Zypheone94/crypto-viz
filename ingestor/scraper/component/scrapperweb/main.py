import sys
import os
import signal
from pathlib import Path
from dotenv import load_dotenv
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from threading import Event
from scrapers.spiders.coindesk_spider import CoinDeskSpider

shutdown_event = Event()

def signal_handler(signum, frame):
    print(f"Received signal {signum}. Shutting down gracefully...")
    shutdown_event.set()
    sys.exit(0)

def run_crawler():
    # Load Scrapy settings
    settings = get_project_settings()

    # Set data/output directory
    data_path = Path(os.getenv("DATA_PATH", "data"))
    data_path.mkdir(parents=True, exist_ok=True)
    settings.set("OUTPUT_DIR", str(data_path))

    # Set pipeline
    settings.set("ITEM_PIPELINES", {
        "scrapers.pipelines.CryptoDataPipeline": 300,
    })

    # Set log file
    log_path = data_path / "logs"
    log_path.mkdir(parents=True, exist_ok=True)
    settings.set("LOG_FILE", str(log_path / "scraper.log"))

    # Optional settings
    settings.set("ROBOTSTXT_OBEY", False)
    settings.set("DOWNLOAD_DELAY", 2)
    settings.set("CONCURRENT_REQUESTS", 1)
    settings.set("RANDOMIZE_DOWNLOAD_DELAY", 0.5)
    settings.set("USER_AGENT", "crypto-viz-scraper/1.0")
    settings.set("LOG_LEVEL", "DEBUG")

    # Start Scrapy process
    process = CrawlerProcess(settings)
    process.crawl(CoinDeskSpider)
    process.start()  # blocking

def main():
    env_file = Path(__file__).resolve().parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)

    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("Starting Crypto Viz Scraper")
    print(f"Data directory: {os.getenv('DATA_PATH', 'data')}")
    print(f"Fetch interval: {os.getenv('FETCH_INTERVAL', '300')} seconds")

    try:
        run_crawler()
    except KeyboardInterrupt:
        print("Shutting down scraper...")
        shutdown_event.set()
    except Exception as e:
        print(f"Error starting scraper: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
