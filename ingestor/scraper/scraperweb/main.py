import sys
import os
import signal
import time
import threading
from pathlib import Path
from dotenv import load_dotenv
from threading import Event

shutdown_event = Event()

def signal_handler(signum, frame):
    print(f"Received signal {signum}. Shutting down gracefully...")
    shutdown_event.set()
    sys.exit(0)

def run_rss_scraper():
    """Run the RSS scraper to fetch from both CoinDesk and CoinTelegraph."""
    from .rss_scraper_poc import main as run_rss_scraper_main
    sources = os.getenv("SOURCES", "coindesk,cointelegraph").split(",")
    print(f"Running RSS scraper for sources: {', '.join(sources)}...")
    run_rss_scraper_main()
    
    # Schedule the next run if not shutting down
    if not shutdown_event.is_set():
        interval = int(os.getenv("FETCH_INTERVAL", "300"))
        print(f"Scheduling next run in {interval} seconds...")
        threading.Timer(interval, run_rss_scraper).start()

def run_crawler():
    """Run Scrapy crawler for more advanced scraping if needed."""
    print("Running Scrapy crawler...")
    
    # Since we're focusing on the RSS scraper, we're leaving this as a stub
    # Uncomment and fix imports if you want to use Scrapy crawlers
    """
    from scrapy.crawler import CrawlerProcess
    from scrapy.utils.project import get_project_settings
    from scraperweb.scrapers.spiders.coindesk_spider import CoinDeskSpider
    
    # Load Scrapy settings
    settings = get_project_settings()

    # Set data/output directory
    data_path = Path(os.getenv("DATA_PATH", "./data"))
    data_path.mkdir(parents=True, exist_ok=True)
    settings.set("OUTPUT_DIR", str(data_path))

    # Set pipeline
    from scraperweb.scrapers.pipelines import CryptoDataPipeline
    settings.set("ITEM_PIPELINES", {
        CryptoDataPipeline: 300,
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
    """
    pass

def run_server():
    """Run the FastAPI server in a separate thread."""
    from .api import run_server as start_api_server
    
    api_thread = threading.Thread(target=start_api_server, daemon=True)
    api_thread.start()
    print(f"API server running on port {os.getenv('SCRAPER_PORT', '8000')}")
    return api_thread

def main():
    # Load configuration from .env
    env_file = Path(__file__).resolve().parent / ".env"
    if env_file.exists():
        print(f"Loading configuration from: {env_file}")
        load_dotenv(env_file)
    else:
        print("Warning: No .env configuration file found. Using default values.")

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("==================================")
    print("=== Crypto Viz Scraper v1.0.0 ===")
    print("==================================")
    print(f"Data directory: {os.getenv('DATA_PATH', './data')}")
    print(f"Fetch interval: {os.getenv('FETCH_INTERVAL', '300')} seconds")
    print(f"API server port: {os.getenv('SCRAPER_PORT', '8000')}")
    print(f"Sources: {os.getenv('SOURCES', 'coindesk,cointelegraph')}")
    print(f"Force write: {os.getenv('FORCE_WRITE', 'false')}")

    try:
        # Start API server in a separate thread
        run_server()
        
        # Run RSS scraper immediately and schedule subsequent runs
        run_rss_scraper()
        
        # Block the main thread to keep the program running
        # This is needed since the API server runs in a daemon thread
        while not shutdown_event.is_set():
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("Shutting down scraper...")
        shutdown_event.set()
    except Exception as e:
        print(f"Error starting scraper: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
