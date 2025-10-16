import os
import json
import time
import hashlib
from typing import Iterable, Tuple, Optional
from pathlib import Path

from .logging_json import log_json
from .models import ArticleModel
from .io_ndjson import write_ndjson as write_to_filesystem

# Check if kafka-python is installed
KAFKA_AVAILABLE = False
try:
    import importlib.util
    kafka_spec = importlib.util.find_spec("kafka")
    if kafka_spec is not None:
        KAFKA_AVAILABLE = True
        log_json("info", "kafka-python module found and available")
    else:
        log_json("warning", "kafka-python module not installed. "
               "Run 'pip install kafka-python' to use Kafka mode")
except ImportError:
    log_json("warning", "Unable to verify if kafka-python is installed")

# Read configuration from environment variables
INGEST_SINK = os.getenv("INGEST_SINK", "filesystem").lower()
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9094")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "news.raw")
KAFKA_SECURITY_PROTOCOL = os.getenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT")
KAFKA_RETRIES = int(os.getenv("KAFKA_RETRIES", "5"))
KAFKA_RETRY_BACKOFF_MS = int(os.getenv("KAFKA_RETRY_BACKOFF_MS", "500"))
KAFKA_MAX_IN_FLIGHT = int(os.getenv("KAFKA_MAX_IN_FLIGHT", "5"))

class KafkaSink:
    """Kafka destination for data."""
    
    def __init__(self):
        self.producer = None
        self.topic = KAFKA_TOPIC
        self.bootstrap_servers = KAFKA_BOOTSTRAP
        self.security_protocol = KAFKA_SECURITY_PROTOCOL
        
    def _ensure_producer(self):
        """Lazy initialization of the Kafka producer."""
        if self.producer is None:
            if not KAFKA_AVAILABLE:
                log_json("error", "kafka-python module not installed. "
                        "Run 'pip install kafka-python'")
                raise ImportError("kafka-python module not installed")
                
            try:
                # pylint: disable=import-error
                from kafka import KafkaProducer  # type: ignore
                from kafka.admin import KafkaAdminClient, NewTopic  # type: ignore
                from kafka.errors import TopicAlreadyExistsError  # type: ignore
                # pylint: enable=import-error
                
                # Create topic if necessary
                try:
                    admin = KafkaAdminClient(
                        bootstrap_servers=self.bootstrap_servers,
                        security_protocol=self.security_protocol
                    )
                    admin.create_topics([
                        NewTopic(
                            name=self.topic,
                            num_partitions=1,
                            replication_factor=1
                        )
                    ])
                    log_json("info", f"Topic '{self.topic}' created")
                except TopicAlreadyExistsError:
                    pass
                except Exception as e:
                    # Non-blocking if auto-create is enabled
                    log_json("warning", f"Topic creation skipped: {e}")
                
                # Initialize producer
                self.producer = KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    security_protocol=self.security_protocol,
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                    key_serializer=lambda k: k.encode("utf-8"),
                )
                
                log_json("info", "Kafka producer initialized", 
                        bootstrap=self.bootstrap_servers,
                        topic=self.topic)
                
            except ImportError:
                log_json("error", "kafka-python module not installed. "
                       "Run 'pip install kafka-python'")
                raise
            except Exception as e:
                log_json("error", f"Kafka producer initialization error: {e}")
                raise
    
    def write(self, base_dir: str, items: Iterable[ArticleModel], 
             source_prefix: Optional[str] = None) -> Tuple[int, Path]:
        """
        Send articles to Kafka.
        
        Args:
            base_dir: Base directory (ignored for Kafka)
            items: Articles to send
            source_prefix: Source prefix (for logging only)
            
        Returns:
            Tuple[int, Path]: Number of items written and virtual path
        """
        self._ensure_producer()
        items_list = list(items)
        if not items_list:
            return 0, Path(base_dir)
        
        count = 0
        for item in items_list:
            try:
                # Convert Pydantic model to dictionary
                try:
                    data = item.model_dump()  # Pydantic v2
                except AttributeError:
                    data = item.dict()  # Pydantic v1
                    
                # Generate key from URL and title (for deduplication)
                key = hashlib.sha1((
                    (data.get("url") or "") + 
                    (data.get("title") or "")
                ).encode("utf-8")).hexdigest()
                
                # Send to Kafka
                self.producer.send(self.topic, key=key, value=data)
                count += 1
                
            except Exception as e:
                log_json("error", f"Error sending to Kafka: {e}")
        
        # Ensure all messages are sent
        self.producer.flush()
        
        log_json(
            "info", 
            f"Sent {count} articles to Kafka",
            topic=self.topic, 
            source=source_prefix or "unknown"
        )
        
        # Return a virtual path for compatibility with write_ndjson API
        return count, Path(base_dir) / f"kafka-{int(time.time())}.virtual"

def write_to_sink(base_dir: str, items: Iterable[ArticleModel], 
                 source_prefix: Optional[str] = None, 
                 force_write: bool = False) -> Tuple[int, Path]:
    """
    Write data to the configured destination (filesystem or Kafka).
    
    Args:
        base_dir: Base directory for file writing
        items: Articles to write
        source_prefix: Source prefix
        force_write: Force write even if duplicate (for filesystem)
        
    Returns:
        Tuple[int, Path]: Number of items written and path
    """
    # Check configured sink
    if INGEST_SINK == "kafka":
        try:
            kafka_sink = KafkaSink()
            return kafka_sink.write(base_dir, items, source_prefix)
        except Exception as e:
            log_json("error", f"Failed writing to Kafka: {e}", fallback="filesystem")
            # Fallback to filesystem in case of error
            return write_to_filesystem(base_dir, items, source_prefix, force_write)
    else:
        # Default sink: filesystem
        return write_to_filesystem(base_dir, items, source_prefix, force_write)