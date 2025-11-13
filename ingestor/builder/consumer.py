import os
import time
import json
import hashlib
import pathlib
import io
import codecs
import re
from typing import Iterable, Dict, List

import pika
import polars as pl
from loguru import logger
from dotenv import load_dotenv

# -------------------- Helpers --------------------
def _clean_text(s: str | None) -> str | None:
    if s is None:
        return None
    s = s.encode("utf-8", errors="ignore").decode("utf-8")
    s = re.sub(r"\s+", " ", s.strip())
    return s

def _id(article: Dict) -> str:
    return hashlib.sha1(((article.get("url") or "") + (article.get("title") or "")).encode("utf-8")).hexdigest()

def normalize(a: Dict) -> Dict:
    return {
        "id": a.get("id") or _id(a),
        "title": a.get("title"),
        "url": a.get("url"),
        "source": a.get("source"),
        "published_at": a.get("published_at"),
        "fetched_at": a.get("fetched_at"),
        "symbol": a.get("symbol"),
        "price_usd": a.get("price_usd"),
        "market_cap_usd": a.get("market_cap_usd"),
    }

# -------------------- Config --------------------
HERE = pathlib.Path(__file__).resolve().parent
load_dotenv(HERE.parent / ".env")

OUT_DIR = pathlib.Path(os.getenv("OUT_DIR", "../data/clean/parquet"))
RAW_DIR = pathlib.Path(os.getenv("RAW_DIR", "../data/raw"))
REJECT_DIR = OUT_DIR.parent / "_corrupt"

INGEST_SOURCE = os.getenv("INGEST_SOURCE", "rabbitmq").lower()

# RabbitMQ
RABBIT_HOST = os.getenv("RABBIT_HOST", "rabbitmq")
RABBIT_PORT = int(os.getenv("RABBIT_PORT", 5672))
RABBIT_USER = os.getenv("RABBIT_USER", "user")
RABBIT_PASS = os.getenv("RABBIT_PASS", "password")
RABBIT_QUEUE = os.getenv("RABBIT_TOPIC", "crypto-viz")

# Batch
BATCH_MAX_MSG = int(os.getenv("BATCH_MAX_MSG", "200"))
BATCH_MAX_SEC = int(os.getenv("BATCH_MAX_SEC", "5"))
SLEEP_SEC = int(os.getenv("BUILDER_POLL_INTERVAL", "5"))

# -------------------- Dedup --------------------
SEEN_IDS: set[str] = set()

# -------------------- Batch flush --------------------
def flush_batch(batch: List[Dict]) -> int:
    if not batch:
        return 0

    dedup: dict[str, dict] = {}
    for r in batch:
        rid = r.get("id") or _id(r)
        r["id"] = rid
        dedup[rid] = r

    new_rows = [r for r in dedup.values() if r["id"] not in SEEN_IDS]
    if not new_rows:
        return 0
    SEEN_IDS.update(r["id"] for r in new_rows)

    df = pl.DataFrame(new_rows)

    df = df.with_columns([
        pl.col("published_at")
          .cast(pl.Utf8)
          .str.replace(r"Z$", "+00:00")
          .str.strptime(pl.Datetime, format="%Y-%m-%dT%H:%M:%S%z", strict=False)
          .dt.convert_time_zone("UTC")
          .alias("ts")
    ])

    invalid = (
        df.filter(pl.col("ts").is_null())
          .with_columns(pl.col("published_at").alias("_corrupt_record"))
          .select([
              "id","title","url","source","published_at","fetched_at",
              "symbol","price_usd","market_cap_usd","_corrupt_record"
          ])
    )

    valid = df.filter(pl.col("ts").is_not_null())

    valid = (
        valid.with_columns([
            pl.col("title").map_elements(_clean_text, return_dtype=pl.Utf8),
            pl.col("url").cast(pl.Utf8).map_elements(_clean_text, return_dtype=pl.Utf8),
            pl.col("source").cast(pl.Utf8).map_elements(_clean_text, return_dtype=pl.Utf8),
            pl.col("symbol").cast(pl.Utf8).map_elements(_clean_text, return_dtype=pl.Utf8),
            pl.col("price_usd").cast(pl.Float64),
            pl.col("market_cap_usd").cast(pl.Float64),
            pl.col("ts").dt.date().alias("date"),
        ])
        .select([
            "id","ts","date","title","url","source","fetched_at",
            "symbol","price_usd","market_cap_usd"
        ])
    )

    if invalid.height > 0:
        REJECT_DIR.mkdir(parents=True, exist_ok=True)
        rej_path = REJECT_DIR / f"reject-{int(time.time())}.ndjson"
        with open(rej_path, "w", encoding="utf-8") as f:
            for rec in invalid.to_dicts():
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        logger.warning(json.dumps({
            "service":"builder","mode":INGEST_SOURCE,"msg":"corrupt_rows",
            "count": invalid.height, "reject_file": str(rej_path)
        }))

    written = 0
    for key, g in valid.group_by("date"):
        date_value = key[0] if isinstance(key, tuple) else key
        folder = getattr(date_value, "isoformat", lambda: str(date_value))()
        outdir = OUT_DIR / f"date={folder}"
        outdir.mkdir(parents=True, exist_ok=True)
        outpath = outdir / f"part-{int(time.time())}.parquet"
        g.write_parquet(outpath)
        logger.info(json.dumps({
            "service":"builder","mode":INGEST_SOURCE,"msg":"parquet_written",
            "date": folder, "rows": g.height, "path": str(outpath)
        }))
        written += g.height

    return written

# -------------------- Sources --------------------
def filesystem_source() -> Iterable[Dict]:
    for p in sorted(RAW_DIR.rglob("*.ndjson")):
        raw = p.read_bytes()
        if raw[:3] == codecs.BOM_UTF8:
            raw = raw[3:]
        text = raw.decode("utf-8", errors="replace")
        for line in io.StringIO(text).read().splitlines():
            line = line.strip()
            if not line:
                continue
            yield normalize(json.loads(line))

def rabbitmq_source(queue: str = RABBIT_QUEUE) -> Iterable[Dict]:
    credentials = pika.PlainCredentials(RABBIT_USER, RABBIT_PASS)
    parameters = pika.ConnectionParameters(host=RABBIT_HOST, port=RABBIT_PORT, credentials=credentials)

    max_attempts = 10
    for attempt in range(max_attempts):
        try:
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            channel.queue_declare(queue=queue, durable=True)
            logger.info(f"[builder] Connected to RabbitMQ at {RABBIT_HOST}:{RABBIT_PORT}")
            break
        except pika.exceptions.AMQPConnectionError:
            logger.warning(f"[builder] RabbitMQ not ready, retry {attempt+1}/{max_attempts}...")
            time.sleep(2)
    else:
        raise Exception(f"[builder] Cannot connect to RabbitMQ after {max_attempts} attempts")

    try:
        for method_frame, properties, body in channel.consume(queue=queue, inactivity_timeout=1):
            if body is None:
                continue
            try:
                data = json.loads(body.decode("utf-8"))
                print("data", data)
                yield normalize(data)
                channel.basic_ack(method_frame.delivery_tag)
            except Exception as e:
                logger.error(f"[builder] skip corrupt message: {e}")
    finally:
        channel.cancel()
        connection.close()

def choose_source() -> Iterable[Dict]:
    if INGEST_SOURCE == "rabbitmq":
        return rabbitmq_source()
    if INGEST_SOURCE == "filesystem":
        return filesystem_source()
    raise ValueError(f"INGEST_SOURCE must be 'rabbitmq' or 'filesystem', got '{INGEST_SOURCE}'")

# -------------------- Main loop --------------------
def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.add(lambda m: print(m, end=""))
    logger.info(json.dumps({
        "service":"builder",
        "msg":"consumer_start",
        "mode":INGEST_SOURCE,
        "rabbit_host": RABBIT_HOST if INGEST_SOURCE=='rabbitmq' else None,
        "queue": RABBIT_QUEUE if INGEST_SOURCE=='rabbitmq' else None,
        "raw_dir": str(RAW_DIR.resolve()) if INGEST_SOURCE=='filesystem' else None
    }))

    src = choose_source()
    batch, t0 = [], time.time()

    try:
        for rec in src:
            batch.append(rec)
            now = time.time()
            if len(batch) >= BATCH_MAX_MSG or (now - t0) >= BATCH_MAX_SEC:
                try:
                    n = flush_batch(batch)
                except Exception as e:
                    logger.error(json.dumps(
                        {"service": "builder", "mode": INGEST_SOURCE, "msg": "flush_failed", "error": str(e)}))
                    n = 0
                logger.info(json.dumps(
                    {"service": "builder", "mode": INGEST_SOURCE, "msg": "batch_flushed",
                     "batch_size": len(batch), "rows_written": n}))
                batch.clear()
                t0 = now
    except KeyboardInterrupt:
        logger.info(json.dumps({"service": "builder", "msg": "shutdown_requested"}))
    finally:
        if batch:
            n = flush_batch(batch)
            logger.info(json.dumps(
                {"service": "builder", "mode": INGEST_SOURCE, "msg": "final_flush",
                 "batch_size": len(batch), "rows_written": n}))

if __name__ == "__main__":
    main()
