import os
import sys
import threading
from pathlib import Path

# Add parent directory to path for imports
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

# Import after path setup
try:
    # Import from same directory (scrapers)
    from scraperweb.scrapers.rss import COINDESK_RSS, COINTELEGRAPH_RSS, fetch_rss, parse_rss
    # Import from parent directory (scraperweb)
    from scraperweb.sink import write_to_sink
    from scraperweb.logging_json import log_json
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

# Use relative path that works from any environment
data_dir = Path(__file__).resolve().parent.parent.parent.parent / "data"

def fetch_with_timeout(url, source, timeout_minutes):
    """
    Fetch RSS with a timeout.
    
    Returns:
        tuple: (success, xml_text or None, error message or None)
    """
    result = [False, None, None]
    
    def _fetch():
        try:
            xml_text = fetch_rss(url)
            result[0] = True
            result[1] = xml_text
        except Exception as e:
            result[2] = str(e)
    
    # Start fetch in a separate thread
    thread = threading.Thread(target=_fetch)
    thread.daemon = True
    thread.start()
    
    # Wait for the thread to complete or timeout
    thread.join(timeout_minutes * 60)
    
    if thread.is_alive():
        # Timeout occurred
        return False, None, "Fetch timeout exceeded"
    
    return result[0], result[1], result[2]

def main():
    # Get sources from environment
    source_names = os.getenv("SOURCES", "coindesk,cointelegraph").lower().split(",")
    sources = []
    
    if "coindesk" in source_names:
        sources.append((COINDESK_RSS, "coindesk"))
    
    if "cointelegraph" in source_names:
        sources.append((COINTELEGRAPH_RSS, "cointelegraph"))
        
    errors = []
    
    # Process each source separately and save to individual files
    for url, source in sources:
        try:
            # Fetch RSS data directly
            xml_text = fetch_rss(url)
            articles = list(parse_rss(xml_text, source))
            log_json("info", "Fetched articles", source=source, count=len(articles))
            
            # Write articles directly to raw data folder (no cache)
            if articles:
                force = bool(os.getenv("FORCE_WRITE", "False").lower() == "true")
                written, out_file = write_to_sink(str(data_dir), articles, source_prefix=source, force_write=force)
                log_json("info", f"{source} articles written", 
                       file=str(out_file), 
                       written_count=written)
                       
        except Exception as e:
            log_json("error", "Failed to fetch/parse", source=source, error=str(e))
            errors.append({"source": source, "error": str(e)})

    if not sum(1 for s, _ in sources if s):
        log_json("warning", "No articles to write", written_count=0)

    if errors:
        log_json("error", "Errors occurred", errors=errors)

if __name__ == "__main__":
	main()
