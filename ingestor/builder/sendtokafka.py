from dotenv import load_dotenv, find_dotenv; load_dotenv(find_dotenv(usecwd=True))
import os, json, hashlib, time
from kafka import KafkaProducer
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError

BOOT = os.getenv("KAFKA_BOOTSTRAP", "localhost:9094")
TOPIC = os.getenv("KAFKA_TOPIC", "news.raw")
SEC = os.getenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT")

def key(a):
    return hashlib.sha1((a["url"] + a["title"]).encode("utf-8")).hexdigest()

try:
    admin = KafkaAdminClient(bootstrap_servers=BOOT, security_protocol=SEC)
    admin.create_topics([NewTopic(name=TOPIC, num_partitions=1, replication_factor=1)])
    print(f"[producer] topic '{TOPIC}' created")
except TopicAlreadyExistsError:
    pass
except Exception as e:
    # pas bloquant si auto-create est ON
    print(f"[producer] topic create skipped: {e}")

producer = KafkaProducer(
    bootstrap_servers=BOOT,
    security_protocol=SEC,
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    key_serializer=lambda k: k.encode("utf-8"),
)

msgs = [
    {"title":"Hello A","url":"https://ex/a","source":"test",
     "published_at":"2025-09-18T10:00:00Z","fetched_at":"2025-09-18T10:00:05Z"},
    {"title":"Hello B","url":"https://ex/b","source":"test",
     "published_at":"2025-09-18T11:00:00Z","fetched_at":"2025-09-18T11:00:05Z"},
]

for a in msgs:
    producer.send(TOPIC, key=key(a), value=a)
producer.flush()
print(f"[producer] sent {len(msgs)} messages to {BOOT} topic {TOPIC}")
time.sleep(0.2)
