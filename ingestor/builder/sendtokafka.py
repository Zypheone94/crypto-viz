from dotenv import load_dotenv, find_dotenv; load_dotenv(find_dotenv(usecwd=True))
import os, json, hashlib, pathlib, codecs
from kafka import KafkaProducer
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError

BOOT = os.getenv("KAFKA_BOOTSTRAP", "localhost:9094")
TOPIC = os.getenv("KAFKA_TOPIC", "crypto-viz")
SEC  = os.getenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT")
RAW_ROOT = pathlib.Path(os.getenv("RAW_DIR", "data/raw"))

def key(a: dict) -> str:
    return hashlib.sha1(((a.get("url") or "") + (a.get("title") or "")).encode("utf-8")).hexdigest()

try:
    KafkaAdminClient(bootstrap_servers=BOOT, security_protocol=SEC)\
        .create_topics([NewTopic(name=TOPIC, num_partitions=1, replication_factor=1)])
except TopicAlreadyExistsError:
    pass
except Exception as e:
    print("[producer] topic create skipped:", e)

producer = KafkaProducer(
    bootstrap_servers=BOOT,
    security_protocol=SEC,
    value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
    key_serializer=lambda k: k.encode("utf-8"),
    acks="all", retries=3, linger_ms=20
)

total = 0
files = sorted(RAW_ROOT.rglob("*.ndjson"))
print(f"[producer] scanning {RAW_ROOT} → {len(files)} file(s)")

for p in files:
    raw = p.read_bytes()
    if raw[:3] == codecs.BOM_UTF8:
        raw = raw[3:]
    text = raw.decode("utf-8", errors="replace")

    sent = 0
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            a = json.loads(line)
            producer.send(TOPIC, key=key(a), value=a)
            sent += 1
        except Exception as e:
            print(f"[producer] skip bad line in {p.name}: {e}")
    if sent:
        print(f"[producer] {p} → sent {sent} message(s)")
        total += sent

producer.flush(); producer.close()
print(f"[producer] done: sent {total} message(s) to {BOOT} topic {TOPIC}")
