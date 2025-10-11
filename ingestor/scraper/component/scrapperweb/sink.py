import os, json, hashlib, pathlib, time
from datetime import datetime, timezone
from ingestor.scraper.component.scrapperweb.logging_json import log_json
from confluent_kafka import Producer


def _now_utc():
    return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")

def article_key(a: dict) -> str:
    return hashlib.sha1(((a.get("url") or "") + (a.get("title") or "")).encode("utf-8")).hexdigest()

class FilesystemSink:
    def __init__(self, root=None):
        self.root = pathlib.Path(root or os.getenv("RAW_DIR", "data/raw"))

    def write(self, article: dict):
        ts = (article.get("fetched_at") or article.get("published_at") or _now_utc())
        y, m, d = ts[:4], ts[5:7], ts[8:10]
        outdir = self.root / y / m / d
        outdir.mkdir(parents=True, exist_ok=True)
        path = outdir / f"part-{int(time.time())}.ndjson"
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(article, ensure_ascii=False) + "\n")
        log_json("scraper", "info")

    def close(self): pass

class KafkaSink:
    def __init__(self, bootstrap=None, topic=None):
        self.topic = topic or os.getenv("KAFKA_TOPIC", "crypto-viz")
        self.p = Producer({
            "bootstrap.servers": bootstrap or os.getenv("KAFKA_BOOTSTRAP","localhost:9094"),
            "acks": "all",
            "enable.idempotence": True,
            "compression.type": "zstd",
            "linger.ms": 50,
            "batch.num.messages": 1000,
            "message.timeout.ms": 30000,
            "client.id": "scraper-producer",
        })

    def _delivery_cb(self, err, msg):
        if err:
            log_json("scraper","warn")

    def write(self, article: dict):
        key = article_key(article)
        payload = json.dumps(article, ensure_ascii=False).encode("utf-8")
        backoff = 0.2
        for _ in range(8):
            try:
                self.p.produce(self.topic, key=key, value=payload, on_delivery=self._delivery_cb)
                self.p.poll(0)
                return
            except BufferError:
                time.sleep(backoff); backoff = min(backoff*2, 2.0)
        log_json("scraper","error")

    def close(self):
        remain = self.p.flush(10.0)
        if remain > 0:
            log_json("scraper","warn")

def build_sink():
    mode = (os.getenv("INGEST_SINK","filesystem") or "filesystem").lower()
    if mode == "kafka":
        return KafkaSink()
    return FilesystemSink()
