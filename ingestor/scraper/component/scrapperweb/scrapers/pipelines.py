import json
import sys
import os
from pathlib import Path
from typing import Dict, Any

sys.path.append(str(Path(__file__).parent.parent))

try:
    # local helper that wraps kafka-python; optional import, will be no-op when disabled
    from kafka_producer import KafkaProducerClient
except Exception:
    KafkaProducerClient = None


class CryptoDataPipeline:
    """Pipeline to save all crypto data in a single NDJSON file and optionally publish to Kafka.

    Configuration via crawler settings or environment variables:
      - OUTPUT_FILE: path to the ndjson file
      - KAFKA_ENABLED: 'true' to enable Kafka
      - KAFKA_TOPIC: topic name
      - KAFKA_BOOTSTRAP_SERVERS: comma separated bootstrap servers
    """

    def __init__(self, output_file: str, kafka_enabled: bool = False, kafka_bootstrap: str | None = None, kafka_topic: str | None = None):
        self.output_file = Path(output_file)
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        self.items_count = 0

        # Kafka client (optional)
        self.kafka_client = None
        if kafka_enabled and KafkaProducerClient is not None:
            try:
                self.kafka_client = KafkaProducerClient(bootstrap_servers=kafka_bootstrap, topic=kafka_topic)
            except Exception:
                # Safe fallback to file-only behavior
                self.kafka_client = None

    @classmethod
    def from_crawler(cls, crawler):
        """Create pipeline instance from crawler settings"""
        output_file = crawler.settings.get('OUTPUT_FILE', './data/articles.ndjson')
        # allow crawler settings to enable Kafka, otherwise fall back to env
        kafka_enabled = crawler.settings.get('KAFKA_ENABLED', os.getenv('KAFKA_ENABLED', 'false').lower() in ('1', 'true', 'yes'))
        kafka_bootstrap = crawler.settings.get('KAFKA_BOOTSTRAP_SERVERS', os.getenv('KAFKA_BOOTSTRAP_SERVERS'))
        kafka_topic = crawler.settings.get('KAFKA_TOPIC', os.getenv('KAFKA_TOPIC'))
        return cls(output_file, kafka_enabled=kafka_enabled, kafka_bootstrap=kafka_bootstrap, kafka_topic=kafka_topic)

    def open_spider(self, spider):
        """Called when spider is opened"""
        self.spider_name = spider.name
        spider.logger.info(f"Opening spider {self.spider_name}, saving to {self.output_file}")

    def close_spider(self, spider):
        """Called when spider is closed"""
        spider.logger.info(f"Spider {self.spider_name} closed. Total items processed: {self.items_count}")
        # flush kafka client if present
        try:
            if self.kafka_client:
                self.kafka_client.flush()
                self.kafka_client.close()
        except Exception:
            spider.logger.exception("Error closing Kafka client")

    def process_item(self, item: Dict[str, Any], spider):
        """Append each item to the NDJSON file and optionally publish to Kafka"""
        try:
            # Append to file (behaviour preserved)
            with open(self.output_file, 'a', encoding='utf-8') as f:
                json.dump(item, f, ensure_ascii=False, separators=(',', ':'))
                f.write('\n')

            self.items_count += 1

            # Publish to Kafka if enabled
            if self.kafka_client:
                try:
                    self.kafka_client.send(item)
                except Exception:
                    spider.logger.exception("Failed to send item to Kafka")

            # Log progress every 10 items
            if self.items_count % 10 == 0:
                spider.logger.info(f"Processed {self.items_count} items from {self.spider_name}")

            return item

        except Exception:
            spider.logger.exception("Error processing item")
            return item
