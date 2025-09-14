import json
import sys
from pathlib import Path
from typing import Dict, Any

sys.path.append(str(Path(__file__).parent.parent))

class CryptoDataPipeline:
    """Pipeline to save all crypto data in a single NDJSON file"""
    
    def __init__(self, output_file: str):
        self.output_file = Path(output_file)
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        self.items_count = 0
    
    @classmethod
    def from_crawler(cls, crawler):
        """Create pipeline instance from crawler settings"""
        output_file = crawler.settings.get('OUTPUT_FILE', './data/articles.ndjson')
        return cls(output_file)
    
    def open_spider(self, spider):
        """Called when spider is opened"""
        self.spider_name = spider.name
        spider.logger.info(f"Opening spider {self.spider_name}, saving to {self.output_file}")
    
    def close_spider(self, spider):
        """Called when spider is closed"""
        spider.logger.info(f"Spider {self.spider_name} closed. Total items processed: {self.items_count}")
    
    def process_item(self, item: Dict[str, Any], spider):
        """Append each item to the NDJSON file"""
        try:
            with open(self.output_file, 'a', encoding='utf-8') as f:
                json.dump(item, f, ensure_ascii=False, separators=(',', ':'))
                f.write('\n')
            
            self.items_count += 1
            # Log progress every 10 items
            if self.items_count % 10 == 0:
                spider.logger.info(f"Processed {self.items_count} items from {self.spider_name}")
            
            return item
        
        except Exception as e:
            spider.logger.error(f"Error processing item: {e}")
            return item
