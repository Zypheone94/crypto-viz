import sys
import os
import signal
import time
import threading
from pathlib import Path
from dotenv import load_dotenv
from threading import Event

current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

shutdown_event = Event()

def signal_handler(signum, frame):
    print(f"Received signal {signum}. Shutting down gracefully...")
    shutdown_event.set()
    sys.exit(0)

def run_rss_scraper():
    """Run the RSS scraper to fetch from both CoinDesk and CoinTelegraph."""
    from scraperweb.scrapers.rss_scraper_poc import main as run_rss_scraper_main
    sources = os.getenv("SOURCES", "coindesk,cointelegraph").split(",")
    print(f"Running RSS scraper for sources: {', '.join(sources)}...")
    run_rss_scraper_main()
    
    # Schedule the next run if not shutting down
    if not shutdown_event.is_set():
        interval = int(os.getenv("FETCH_INTERVAL", "300"))
        print(f"Scheduling next run in {interval} seconds...")
        threading.Timer(interval, run_rss_scraper).start()

def run_price_scraper():
    """Run the CoinDesk price scraper with AI summaries."""
    print("Running CoinDesk price and article scraper...")
    
    try:
        from scraperweb.scrapers.coindesk_price_data_scraper import run_coindesk_price_scraper
        
        # Run the price scraper
        result = run_coindesk_price_scraper()
        
        if result:
            crypto_count = len(result.get('crypto_data', []))
            article_count = len(result.get('article_summaries', []))
            print("CoinDesk price scraping completed:")
            print(f"  - {crypto_count} cryptocurrencies with price data")
            print(f"  - {article_count} articles with AI summaries")
        else:
            print("CoinDesk price scraping completed but no data found.")
            
    except Exception as e:
        print(f"Error in CoinDesk price scraper: {e}")
    
    # Schedule the next run
    if not shutdown_event.is_set():
        # Run price scraper every hour by default
        interval = int(os.getenv("CRYPTO_FETCH_INTERVAL", "3600"))
        print(f"Scheduling next price scraper run in {interval} seconds...")
        threading.Timer(interval, run_price_scraper).start()

def run_server():
    """Run the FastAPI server in a separate thread."""
    from scraperweb.api import run_server as start_api_server
    
    api_thread = threading.Thread(target=start_api_server, daemon=True)
    api_thread.start()
    print(f"API server running on port {os.getenv('SCRAPER_PORT', '8001')}")
    return api_thread

def main():
    # Load configuration from .env
    env_file = Path(__file__).resolve().parent / "scraperweb" / ".env"
    if env_file.exists():
        print(f"Loading configuration from: {env_file}")
        load_dotenv(env_file)
    else:
        print("Warning: No .env configuration file found. Using default values.")

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("Crypto Viz Scraper")
    # Set data path to the existing ingestor/data folder (absolute path)
    # main.py is in ingestor/scraper/, so we go up one level to ingestor/, then to data/
    script_dir = Path(__file__).parent  # ingestor/scraper/
    ingestor_dir = script_dir.parent     # ingestor/
    data_dir = ingestor_dir / "data"     # ingestor/data/
    
    # Use environment variable if set, otherwise use the calculated path
    env_data_path = os.getenv('DATA_PATH')
    if env_data_path:
        # If env path is relative, make it relative to the script directory
        if not Path(env_data_path).is_absolute():
            data_path = str(script_dir / env_data_path)
        else:
            data_path = env_data_path
    else:
        data_path = str(data_dir)
    
    # Normalize the path and set it in environment for other modules
    data_path = str(Path(data_path).resolve())
    os.environ['DATA_PATH'] = data_path
    
    print(f"Data directory: {data_path}")
    print(f"RSS fetch interval: {os.getenv('FETCH_INTERVAL', '300')} seconds")
    print(f"Crypto data fetch interval: {os.getenv('CRYPTO_FETCH_INTERVAL', '3600')} seconds")
    print(f"Prompt generation interval: {os.getenv('PROMPT_GEN_INTERVAL', '21600')} seconds")
    print(f"API server port: {os.getenv('SCRAPER_PORT', '8000')}")
    print(f"Sources: {os.getenv('SOURCES', 'coindesk,cointelegraph')}")
    print(f"Force write: {os.getenv('FORCE_WRITE', 'false')}")
    print("Price source: CoinDesk Price Page (https://www.coindesk.com/price)")

    try:
        # Start API server in a separate thread
        run_server()
        
        # Run RSS scraper immediately and schedule subsequent runs
        run_rss_scraper()
        
        # Run CoinDesk price scraper immediately and schedule subsequent runs
        run_price_scraper()
        
        # Import and run the ChatGPT prompt generator
        from scraperweb.prompt_generator import generate_chatgpt_prompt
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
