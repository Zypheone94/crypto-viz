import os
from pathlib import Path
from .rss import COINDESK_RSS, COINTELEGRAPH_RSS, fetch_rss, parse_rss
from .sink import write_to_sink
from .logging_json import log_json

BASE_DIR = Path(__file__).resolve().parent.parent.parent

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
			xml_text = fetch_rss(url)
			articles = list(parse_rss(xml_text, source))
			log_json("info", "Fetched articles", source=source, count=len(articles))
			
			if articles:
				# Add a source identifier to the filename by including it in the base directory
				source_dir = str(BASE_DIR)
				# Use force_write=True to ensure we write articles even if they're duplicates
				# This is useful for testing and to ensure we always get new content with HTML stripped
				force = bool(os.getenv("FORCE_WRITE", "False").lower() == "true")
				written, out_file = write_to_sink(source_dir, articles, source_prefix=source, force_write=force)
				log_json("info", f"{source} articles written", file=str(out_file), written_count=written)
		except Exception as e:
			log_json("error", "Failed to fetch/parse", source=source, error=str(e))
			errors.append({"source": source, "error": str(e)})

	if not sum(1 for s, _ in sources if s):
		log_json("warning", "No articles to write", written_count=0)

	if errors:
		log_json("error", "Errors occurred", errors=errors)

if __name__ == "__main__":
	main()
