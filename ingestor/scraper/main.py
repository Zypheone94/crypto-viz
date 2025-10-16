<<<<<<< HEAD
import sys
import os
import signal
from pathlib import Path
from threading import Event
from dotenv import load_dotenv

# Add the scraper directory to Python path
sys.path.append(str(Path(__file__).parent))

# Add the parent directory (ingestor) to Python path
sys.path.append(str(Path(__file__).parent.parent))

# Scrapy imports
from scraperweb.scrapers.spiders.coindesk_spider import CoinDeskSpider
from scraperweb.rss_scraper_poc import main as run_rss_scraper
from scraperweb.main import main as run_spider_scraper
from scrapy.utils.project import get_project_settings
from scrapy.crawler import CrawlerProcess

# Global shutdown event
shutdown_event = Event()

def signal_handler(signum, frame):
    print(f"Received signal {signum}. Shutting down gracefully...")
    shutdown_event.set()
    sys.exit(0)

def run_crawler():
    """Run multiple Scrapy spiders."""
    settings = get_project_settings()

    # Setup directories - use the data/raw directory structure
    data_path = Path(os.getenv("DATA_PATH", str(Path(__file__).parent.parent / "data" / "raw")))
    data_path.mkdir(parents=True, exist_ok=True)
    settings.set("OUTPUT_DIR", str(data_path))

    # Import all spiders
    try:
        # Import spiders
        from scraperweb.scrapers.spiders.coindesk_spider import CoinDeskSpider
        from scraperweb.scrapers.spiders.coingecko_spider import CoinGeckoSpider
        from scraperweb.scrapers.pipelines import CryptoDataPipeline
        
        # Set pipeline
        settings.set("ITEM_PIPELINES", {
            CryptoDataPipeline: 300,
        })
        
        # Set custom setting for file output naming
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        settings.set("OUTPUT_FILE_PREFIX", f"scrapy_{timestamp}")
        
        # Return the list of spiders to run
        return [CoinDeskSpider, CoinGeckoSpider], settings
        
    except Exception as e:
        print(f"Error configuring spiders: {e}")
        import traceback
        print(traceback.format_exc())
        return [], settings

    # Logs
    log_path = data_path / "logs"
    log_path.mkdir(parents=True, exist_ok=True)
    settings.set("LOG_FILE", str(log_path / "scraper.log"))

    # Optional Scrapy configs
    settings.set("ROBOTSTXT_OBEY", False)
    settings.set("DOWNLOAD_DELAY", 2)
    settings.set("CONCURRENT_REQUESTS", 1)
    settings.set("RANDOMIZE_DOWNLOAD_DELAY", 0.5)
    settings.set("USER_AGENT", "crypto-viz-scraper/1.0")
    settings.set("LOG_LEVEL", "DEBUG")

    process = CrawlerProcess(settings)
    process.crawl(CoinDeskSpider)
    process.start()

def main():
    # Try to load env from either root or scraperweb directory
    env_locations = [
        Path(__file__).resolve().parent / ".env",
        Path(__file__).resolve().parent / "scraperweb" / ".env"
    ]
    
    for env_file in env_locations:
        if env_file.exists():
            print(f"Loading environment from: {env_file}")
            load_dotenv(env_file)
            break

    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("=== Starting Crypto Viz Scraper ===")
    print(f"Data directory: {os.getenv('DATA_PATH', './data')}")
    print(f"Fetch interval: {os.getenv('FETCH_INTERVAL', '300')} seconds")

    try:
        print("Running RSS scraper...")
        run_rss_scraper()

        print("Running either Scrapy spiders OR CoinDesk crawler (not both due to Reactor limitations)")
        # Choose one of these, not both - can't restart the reactor
        # Option 1: Run spider scraper from scraperweb.main
        try:
            run_spider_scraper()
        except Exception as e:
            print(f"Spider scraper error: {e}")
            import traceback
            print(traceback.format_exc())
            
            # Option 2: Try run_crawler instead if the first one failed
            print("Trying direct crawler approach instead...")
            try:
                run_crawler()
                print("Crawler completed successfully.")
            except Exception as e:
                print(f"Crawler error: {e}")
                import traceback
                print(traceback.format_exc())

        print("All scraping tasks completed.")
    except KeyboardInterrupt:
        print("Shutting down scraper...")
        shutdown_event.set()
    except Exception as e:
        print(f"Error starting scraper: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
=======
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import health, metrics
from api.utils.middleware import Middleware
import os
from dotenv import load_dotenv

app = FastAPI()

env_path = os.path.join(os.path.dirname(__file__), '../../../.env')
load_dotenv(env_path)

angular_port = os.getenv("ANGULAR_PORT")
origins = [
    f'http://localhost:{angular_port}'
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.add_middleware(Middleware)

app.include_router(health.router)
app.include_router(metrics.router)
"""
REMINDER : You must start your api path by : 
- API (if you do something with the api, health, etc...)
- Scraper (if your working with the scraper)
- Builder (if your working with the scraper)
it is necessary for the service in the logger to work
"""


@app.get("/")
async def root():
    return {"message": "Hello World"}
>>>>>>> ca5ee0f86d8c1013ec8921cb470f3c2884b419e1
