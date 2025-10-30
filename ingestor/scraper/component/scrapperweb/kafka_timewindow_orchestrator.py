import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List

from kafka_producer import KafkaProducerClient

logger = logging.getLogger(__name__)

class KafkaTimeWindowOrchestrator:
    """
    Orchestrates the scraping process with time windows and Kafka integration.
    Handles both filesystem and Kafka sink modes.
    """

    def __init__(self, 
                 window_size_minutes: int = 60,
                 kafka_producer: Optional[KafkaProducerClient] = None):
        self.window_size = timedelta(minutes=window_size_minutes)
        self.last_window_start = None
        self.kafka_producer = kafka_producer or KafkaProducerClient()
        self.article_cache: Dict[str, dict] = {}
        
    def _generate_message_key(self, article: dict) -> str:
        """Generate a deterministic key for Kafka message deduplication."""
        key_string = f"{article.get('url', '')}{article.get('title', '')}"
        return hashlib.sha1(key_string.encode('utf-8')).hexdigest()

    def should_refresh(self) -> bool:
        """Check if it's time to start a new scraping window."""
        if self.last_window_start is None:
            return True
            
        current_time = datetime.now()
        time_since_last_window = current_time - self.last_window_start
        return time_since_last_window >= self.window_size

    def start_new_window(self):
        """Mark the start of a new scraping window."""
        self.last_window_start = datetime.now()
        self.article_cache.clear()
        logger.info(f"Started new scraping window at {self.last_window_start}")

    def process_article(self, article: dict) -> bool:
        """
        Process a single article, handling both Kafka and filesystem modes.
        Returns True if the article was processed successfully.
        """
        article_key = self._generate_message_key(article)
        
        # Skip if we've already seen this article in the current window
        if article_key in self.article_cache:
            return False
            
        self.article_cache[article_key] = article
        
        # Attempt to send to Kafka if enabled
        if self.kafka_producer.enabled:
            max_retries = 3
            retry_delay = 1.0  # Initial delay in seconds
            
            for attempt in range(max_retries):
                try:
                    success = self.kafka_producer.send(article)
                    if success:
                        logger.debug(f"Successfully sent article to Kafka: {article.get('title')}")
                        return True
                    raise Exception("Kafka send returned False")
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"Failed to send to Kafka (attempt {attempt + 1}/{max_retries}), "
                                     f"retrying in {retry_delay}s: {str(e)}")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        logger.error(f"Failed to send article to Kafka after {max_retries} attempts: {str(e)}")
                        return False
        
        return True

    def get_current_window_articles(self) -> List[dict]:
        """Return all articles collected in the current time window."""
        return list(self.article_cache.values())

    def close(self):
        """Clean up resources."""
        if self.kafka_producer:
            self.kafka_producer.close()
