#!/usr/bin/env python3
"""
Crypto Viz Scrapper - Main startup script
This script starts the crypto data scrapper with proper configuration.
"""

import os
import sys
import signal
from pathlib import Path
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from ingestor.scraper.main import run_server, shutdown_event

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    print(f"\nReceived signal {signum}. Shutting down gracefully...")
    shutdown_event.set()
    sys.exit(0)

def main():
    """Main function to start the scrapper"""
    # Load environment variables
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
    else:
        print("Warning: .env file not found. Using default configuration.")
        print("Copy .env.example to .env and customize as needed.")
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create data directory if it doesn't exist
    data_path = os.getenv("DATA_PATH", "data")
    Path(data_path).mkdir(parents=True, exist_ok=True)
    
    # Create logs directory if it doesn't exist
    log_path = Path(data_path) / "logs"
    log_path.mkdir(parents=True, exist_ok=True)
    
    print("🚀 Starting Crypto Viz Scrapper...")
    print(f"📁 Data directory: {data_path}")
    print(f"⏱️  Fetch interval: {os.getenv('FETCH_INTERVAL', '300')} seconds")
    print(f"🌐 Server port: {os.getenv('SCRAPER_PORT', '8000')}")
    print(f"📊 Sources: {os.getenv('SOURCES', 'coindesk,coingecko')}")
    print("\n📡 Available endpoints:")
    print("  - GET /health - Health check")
    print("  - GET /data/latest - Get latest scraped data")
    print("  - GET /data/export - Export all data")
    print("\n🔄 Scrapper is running continuously...")
    print("Press Ctrl+C to stop.\n")
    
    try:
        # Start the server
        run_server()
    except KeyboardInterrupt:
        print("\n👋 Shutting down scrapper...")
        shutdown_event.set()
    except Exception as e:
        print(f"❌ Error starting scrapper: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
