import os, time, json, hashlib, pathlib, io, codecs
from typing import Iterable, Dict, List
from loguru import logger
import polars as pl
from dotenv import load_dotenv
HERE = pathlib.Path(__file__).resolve().parent
load_dotenv(HERE.parent / "./.env")
OUT_DIR = pathlib.Path(os.getenv("OUT_DIR", "../data/clean/parquet"))
RAW_DIR = pathlib.Path(os.getenv("RAW_DIR", "../data/raw"))
INGEST_SOURCE = os.getenv("INGEST_SOURCE", "kafka").lower()
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9094")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "crypto-viz")
BATCH_MAX_MSG = int(os.getenv("BATCH_MAX_MSG", "200"))
BATCH_MAX_SEC = int(os.getenv("BATCH_MAX_SEC", "5"))

SEEN_IDS: set[str] = set()
def _id(article: Dict) -> str:
    return hashlib.sha1(((article.get("url") or "") + (article.get("title") or "")).encode("utf-8")).hexdigest()

def normalize(a: Dict) -> Dict:
    return {
        "id": _id(a),
        "title": a.get("title"),
        "url": a.get("url"),
        "source": a.get("source"),
        "published_at": a.get("published_at"),
        "fetched_at": a.get("fetched_at"),
    }
def flush_batch(batch: List[Dict]) -> int:

    if not batch:
        return 0

    dedup: dict[str, dict] = {}
    for r in batch:
        rid = r.get("id")
        if not rid:
            rid = hashlib.sha1(((r.get("url") or "") + (r.get("title") or "")).encode("utf-8")).hexdigest()
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
          .alias("ts_parsed")
    ]).with_columns([
        pl.when(pl.col("ts_parsed").is_not_null())
          .then(pl.col("ts_parsed").dt.convert_time_zone("UTC"))
          .otherwise(None)
          .alias("ts")
    ])

    invalid = (df.filter(pl.col("ts").is_null())
                 .with_columns(pl.col("published_at").alias("_corrupt_record"))
                 .select(["id","title","url","source","published_at","fetched_at","_corrupt_record"]))

    valid = (df.filter(pl.col("ts").is_not_null())
               .with_columns(pl.col("ts").dt.date().alias("date"))
               .select(["id","ts","date","title","url","source","fetched_at"]))

    if invalid.height > 0:
        rej_dir = OUT_DIR.parent / "_corrupt"
        rej_dir.mkdir(parents=True, exist_ok=True)
        rej_path = rej_dir / f"reject-{int(time.time())}.ndjson"
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


def kafka_source() -> Iterable[Dict]:
    from kafka import KafkaConsumer
    c = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id=os.getenv("KAFKA_GROUP_ID", "builder-group"),
        security_protocol=os.getenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT"),
        enable_auto_commit=True,
        auto_offset_reset="latest",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )
    for m in c:
        yield normalize(m.value)


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

def choose_source() -> Iterable[Dict]:
    if INGEST_SOURCE == "kafka":
        return kafka_source()
    if INGEST_SOURCE == "filesystem":
        return filesystem_source()
    raise ValueError(f"INGEST_SOURCE must be 'kafka' or 'filesystem', got '{INGEST_SOURCE}'")
def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(lambda m: print(m, end=""))
    logger.info(json.dumps({"service":"builder","msg":"consumer_start","mode":INGEST_SOURCE,
                            "kafka_bootstrap":KAFKA_BOOTSTRAP if INGEST_SOURCE=='kafka' else None,
                            "topic":KAFKA_TOPIC if INGEST_SOURCE=='kafka' else None,
                            "raw_dir": str(RAW_DIR.resolve()) if INGEST_SOURCE=='filesystem' else None}))

    src = choose_source()
    batch, t0 = [], time.time()

    for rec in src:
        batch.append(rec)
        now = time.time()
        if len(batch) >= BATCH_MAX_MSG or (now - t0) >= BATCH_MAX_SEC:
            n = flush_batch(batch)
            logger.info(json.dumps({"service":"builder","mode":INGEST_SOURCE,
                                    "msg":"batch_flushed","batch_size":len(batch),
                                    "rows_written":n}))
            batch.clear()
            t0 = now

if __name__ == "__main__":
    main()
