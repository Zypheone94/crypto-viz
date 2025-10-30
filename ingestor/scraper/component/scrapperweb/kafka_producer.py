import os
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

KAFKA_ENABLED = os.getenv("KAFKA_ENABLED", "false").lower() in ("1", "true", "yes")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "crypto-articles")


class KafkaProducerClient:
    """Small wrapper around kafka-python's KafkaProducer.

    This module keeps the dependency surface low and exposes send/close methods.
    If KAFKA_ENABLED is false it becomes a no-op client.
    """

    def __init__(self, bootstrap_servers: Optional[str] = None, topic: Optional[str] = None):
        self.enabled = KAFKA_ENABLED
        self.topic = topic or KAFKA_TOPIC
        self.bootstrap = bootstrap_servers or KAFKA_BOOTSTRAP
        self._producer = None

        if not self.enabled:
            logger.info("Kafka is disabled (KAFKA_ENABLED not set). Producer will be no-op.")
            return

        try:
            from kafka import KafkaProducer

            # create producer that sends JSON-encoded bytes
            self._producer = KafkaProducer(
                bootstrap_servers=[s.strip() for s in self.bootstrap.split(",") if s.strip()],
                value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
                linger_ms=10,
                retries=3,
            )
            logger.info(f"Kafka producer created for topic '{self.topic}' against {self.bootstrap}")

        except Exception as e:
            # Do not crash the scraper if Kafka isn't reachable — log and disable
            logger.exception("Failed to initialize Kafka producer. Kafka will be disabled.")
            self.enabled = False
            self._producer = None

    def send(self, value: dict):
        if not self.enabled or self._producer is None:
            return False

        try:
            self._producer.send(self.topic, value)
            # fire-and-forget; users can call flush() if they need delivery guarantees
            return True
        except Exception:
            logger.exception("Failed to send message to Kafka")
            return False

    def flush(self, timeout: float = 5.0):
        if not self.enabled or self._producer is None:
            return
        try:
            self._producer.flush(timeout=timeout)
        except Exception:
            logger.exception("Error flushing Kafka producer")

    def close(self):
        if not self.enabled or self._producer is None:
            return
        try:
            self._producer.close()
        except Exception:
            logger.exception("Error closing Kafka producer")


__all__ = ["KafkaProducerClient"]
