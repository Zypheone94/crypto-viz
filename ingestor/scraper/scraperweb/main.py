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
    """Run Scrapy crawler for cryptocurrency price data."""
    print("Running Scrapy crawler for cryptocurrency price data...")
    
    from scrapy.crawler import CrawlerRunner
    from scrapy.utils.project import get_project_settings
    from .scrapers.spiders.coingecko_spider import CoinGeckoSpider
    from twisted.internet import defer
    import logging
    
    # Set up additional logging for crawler
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    )

    # Load Scrapy settings
    settings = get_project_settings()

    # Set data/output directory
    data_path = Path(os.getenv("DATA_PATH", "./data"))
    data_path.mkdir(parents=True, exist_ok=True)
    
    # Make sure the output path exists
    articles_path = data_path / "articles.ndjson"
    articles_dir = articles_path.parent
    articles_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Output will be saved to: {articles_path}")
    
    settings.update({
        "OUTPUT_FILE": str(articles_path),
        "ROBOTSTXT_OBEY": False,
        "DOWNLOAD_DELAY": int(os.getenv("DOWNLOAD_DELAY", "3")),
        "CONCURRENT_REQUESTS": int(os.getenv("CONCURRENT_REQUESTS", "1")),
        "RANDOMIZE_DOWNLOAD_DELAY": 0.5,
        "USER_AGENT": "crypto-viz-scraper/1.0",
        "LOG_LEVEL": "INFO",
        "ITEM_PIPELINES": {
            "scraperweb.scrapers.pipelines.CryptoDataPipeline": 300,
        },
        "FEEDS": {
            str(articles_path): {
                'format': 'jsonlines',
                'encoding': 'utf8',
                'store_empty': False,
                'overwrite': False,
            },
        },
    })

    # Set log file
    log_path = data_path / "logs"
    log_path.mkdir(parents=True, exist_ok=True)
    log_file = log_path / "crawler.log"
    settings["LOG_FILE"] = str(log_file)
    
    print(f"Crawler logs will be saved to: {log_file}")

    # Use CrawlerRunner instead of CrawlerProcess to run non-blocking
    runner = CrawlerRunner(settings)
    
    @defer.inlineCallbacks
    def crawl():
        try:
            print("Starting CoinGecko crawler...")
            yield runner.crawl(CoinGeckoSpider)
            print("CoinGecko crawling completed.")
        except Exception as e:
            print(f"Error in crawler: {e}")
        finally:
            # Without this, the reactor keeps running and may prevent the program from exiting
            # reactor.stop()  # Don't stop the reactor as it might be used by other components
            pass

    # Run the crawler
    crawl()
    
    # Schedule the next run
    if not shutdown_event.is_set():
        # Run crawlers every hour by default (more appropriate for price data)
        interval = int(os.getenv("CRYPTO_FETCH_INTERVAL", "3600"))
        print(f"Scheduling next crawler run in {interval} seconds...")
        threading.Timer(interval, run_crawler).start()

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
    print(f"RSS fetch interval: {os.getenv('FETCH_INTERVAL', '300')} seconds")
    print(f"Crypto data fetch interval: {os.getenv('CRYPTO_FETCH_INTERVAL', '3600')} seconds")
    print(f"Prompt generation interval: {os.getenv('PROMPT_GEN_INTERVAL', '21600')} seconds")
    print(f"API server port: {os.getenv('SCRAPER_PORT', '8000')}")
    print(f"Sources: {os.getenv('SOURCES', 'coindesk,cointelegraph')}")
    print(f"Force write: {os.getenv('FORCE_WRITE', 'false')}")
    print(f"CoinGecko API Key configured: {'Yes' if os.getenv('COINGECKO_API_KEY') else 'No'}")

    try:
        # Start API server in a separate thread
        run_server()
        
        # Run RSS scraper immediately and schedule subsequent runs
        run_rss_scraper()
        
        # Run CoinGecko crawler immediately and schedule subsequent runs
        run_crawler()
        
        # Import and run the ChatGPT prompt generator
        from .prompt_generator import generate_chatgpt_prompt
        generate_chatgpt_prompt()
        
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
