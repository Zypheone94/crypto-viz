import json
import sys
from pathlib import Path
from typing import Dict, Any

sys.path.append(str(Path(__file__).parent.parent))

# Import the sink module
try:
    from ..sink import write_to_sink
except ImportError:
    # Fallback for when module structure is different
    from scraperweb.sink import write_to_sink

class CryptoDataPipeline:
    """Pipeline to save all crypto data in a single NDJSON file"""
    
    def __init__(self, output_file: str):
        self.output_file = Path(output_file)
        # Create parent directories if they don't exist
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        self.items_count = 0
    
    @classmethod
    def from_crawler(cls, crawler):
        """Create pipeline instance from crawler settings"""
        # Get output file path from settings
        output_file = crawler.settings.get('OUTPUT_FILE', './data/articles.ndjson')
        return cls(output_file)
    
    def open_spider(self, spider):
        """Called when spider is opened"""
        self.spider_name = spider.name
        spider.logger.info(f"Opening spider {self.spider_name}, saving to {self.output_file}")
        # Verify the file is writable
        try:
            # Ensure the file is writable
            open(self.output_file, 'a', encoding='utf-8').close()
            spider.logger.info(f"Output file {self.output_file} is writable")
        except Exception as e:
            spider.logger.error(f"ERROR: Output file {self.output_file} is NOT writable: {e}")
    
    def close_spider(self, spider):
        """Called when spider is closed"""
        spider.logger.info(f"Spider {self.spider_name} closed. Total items processed: {self.items_count}")
    
    def process_item(self, item: Dict[str, Any], spider):
        """Process an item using the configured data sink"""
        try:
            # Log detailed item info for debugging
            spider.logger.info(f"Processing item: {item.get('id', 'unknown')}")
            
            # Convert to ArticleModel if needed, but most scrapy items are dicts
            from pydantic import BaseModel
            if isinstance(item, BaseModel):
                # Item is already a pydantic model
                model_item = item
            else:
                # Create a basic model from dict
                from ..models import ArticleModel
                
                # Try to adapt the item to our model structure
                model_data = {
                    "id": item.get("id", ""),
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "source": item.get("source", self.spider_name),
                    "published_at": item.get("published_at", item.get("fetched_at", "")),
                    "fetched_at": item.get("fetched_at", ""),
                    "content": item.get("content", None)
                }
                try:
                    model_item = ArticleModel(**model_data)
                except Exception as e:
                    spider.logger.error(f"Cannot convert item to ArticleModel: {e}")
                    # Fallback to filesystem method
                    with open(self.output_file, 'a', encoding='utf-8') as f:
                        json.dump(item, f, ensure_ascii=False, separators=(',', ':'))
                        f.write('\n')
                    self.items_count += 1
                    return item
            
            # Use the configured sink (kafka or filesystem)
            base_dir = str(self.output_file.parent.parent)  # Get base directory
            written, _ = write_to_sink(
                base_dir=base_dir,
                items=[model_item],
                source_prefix=self.spider_name
            )
            
            self.items_count += 1
            # Log progress every item for CoinGecko, every 10 for others
            if self.spider_name == 'coingecko' or self.items_count % 10 == 0:
                spider.logger.info(f"Processed {self.items_count} items from {self.spider_name}")
            
            return item
        
        except Exception as e:
            spider.logger.error(f"Error processing item: {e}")
            # Print stack trace for debugging
            import traceback
            spider.logger.error(traceback.format_exc())
            return item
