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

def _clean_text(s: str | None) -> str | None:
    if s is None:
        return None
    s = s.encode("utf-8", errors="ignore").decode("utf-8")
    s = re.sub(r"\s+", " ", s.strip())
    return s


def _id(article: Dict) -> str:
    try:
        payload = json.dumps(
            {
                "url": article.get("url"),
                "title": article.get("title"),
                "name": article.get("name"),
                "symbol": article.get("symbol"),
                "published_at": article.get("published_at"),
                "fetched_at": article.get("fetched_at"),
            },
            sort_keys=True,
            ensure_ascii=False,
        )
    except TypeError:
        payload = repr(
            (
                article.get("url"),
                article.get("title"),
                article.get("name"),
                article.get("symbol"),
                article.get("published_at"),
                article.get("fetched_at"),
            )
        )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def normalize(a: Dict) -> Dict:
    return {
        "id": a.get("id") or _id(a),
        "name": a.get("name") or a.get("title"),
        "url": a.get("url"),
        "source": a.get("source"),
        "published_at": a.get("published_at"),
        "fetched_at": a.get("fetched_at"),
        "symbol": a.get("symbol"),
        "price": a.get("price") or a.get("price_usd"),
        "market_cap": a.get("market_cap") or a.get("market_cap_usd"),
        "volume_24h": a.get("volume_24h"),
        "coin_circulating": a.get("coin_circulating"),
    }


HERE = pathlib.Path(__file__).resolve().parent
load_dotenv(HERE.parent / ".env")

OUT_DIR = pathlib.Path(os.getenv("OUT_DIR", "../data/clean/parquet"))
RAW_DIR = pathlib.Path(os.getenv("RAW_DIR", "../data/raw"))
REJECT_DIR = OUT_DIR.parent / "_corrupt"  # pas utilisé ici

INGEST_SOURCE = os.getenv("INGEST_SOURCE", "rabbitmq").lower()

RABBIT_HOST = os.getenv("RABBIT_HOST", "rabbitmq")
RABBIT_PORT = int(os.getenv("RABBIT_PORT", 5672))
RABBIT_USER = os.getenv("RABBIT_USER", "user")
RABBIT_PASS = os.getenv("RABBIT_PASS", "password")
RABBIT_QUEUE = os.getenv("RABBIT_TOPIC", "crypto-viz")

BATCH_MAX_MSG = int(os.getenv("BATCH_MAX_MSG", "200"))
BATCH_MAX_SEC = int(os.getenv("BATCH_MAX_SEC", "60"))
SLEEP_SEC = int(os.getenv("BUILDER_POLL_INTERVAL", "5"))
def flush_batch(batch: List[Dict]) -> int:
    """
    Version ultra tolérante :
    - pas de SEEN_IDS global
    - pas de dédup agressive
    - pas de parsing datetime fragile
    Chaque enregistrement du batch devient une ligne.
    """
    if not batch:
        return 0

    for r in batch:
        if not r.get("id"):
            r["id"] = _id(r)
    try:
        df = pl.from_dicts(batch, infer_schema_length=None)
    except Exception as e:
        logger.error(f"[BUILDER] flush_batch: failed to build DataFrame from dicts: {e}")
        return 0
    df = df.with_columns(
        [
            pl.col("name").cast(pl.Utf8, strict=False).map_elements(_clean_text, return_dtype=pl.Utf8),
            pl.col("url").cast(pl.Utf8, strict=False).map_elements(_clean_text, return_dtype=pl.Utf8),
            pl.col("source").cast(pl.Utf8, strict=False).map_elements(_clean_text, return_dtype=pl.Utf8),
            pl.col("symbol").cast(pl.Utf8, strict=False).map_elements(_clean_text, return_dtype=pl.Utf8),
            pl.col("price").cast(pl.Float64, strict=False),
            pl.col("market_cap").cast(pl.Float64, strict=False),
            pl.col("volume_24h").cast(pl.Float64, strict=False),
            pl.col("coin_circulating").cast(pl.Float64, strict=False),
            pl.col("fetched_at").cast(pl.Utf8, strict=False),
            pl.col("published_at").cast(pl.Utf8, strict=False),
        ]
    )
    df = df.with_columns(
        [
            pl.when(pl.col("fetched_at").str.len_chars() >= 10)
            .then(pl.col("fetched_at").str.slice(0, 10))
            .when(pl.col("published_at").str.len_chars() >= 10)
            .then(pl.col("published_at").str.slice(0, 10))
            .otherwise(pl.lit("unknown"))
            .alias("date")
        ]
    )
    valid = df.select(
        [
            "id",
            "name",
            "url",
            "source",
            "published_at",
            "fetched_at",
            "symbol",
            "price",
            "market_cap",
            "volume_24h",
            "coin_circulating",
            "date",
        ]
    ).filter(
        pl.col("price").is_not_null()
        & pl.col("volume_24h").is_not_null()
        & pl.col("coin_circulating").is_not_null()
    )
    try:
        symbols = (
            valid.select(pl.col("symbol").drop_nulls().unique())
            .to_series()
            .to_list()
        )
        symbols_sample = symbols[:10]
        logger.info(
            f"[BUILDER] batch_in size={valid.height} "
            f"symbols_count={len(symbols)} symbols_sample={symbols_sample}"
        )
    except Exception:
        pass

    written = 0
    for key, g in valid.group_by("date"):
        date_value = key[0] if isinstance(key, tuple) else key
        folder = str(date_value)
        outdir = OUT_DIR / f"date={folder}"
        outdir.mkdir(parents=True, exist_ok=True)
        outpath = outdir / f"part-{int(time.time())}.parquet"

        g.write_parquet(outpath)

        logger.info(
            f"[BUILDER] write_parquet path={outpath} rows={g.height} date={folder}"
        )
        written += g.height

    return written



def filesystem_source() -> Iterable[Dict]:
    """
    Version tolérante :
    - une ligne JSON cassée ne fait pas tomber tout le fichier.
    - on ignore silencieusement les lignes invalides.
    """
    for p in sorted(RAW_DIR.rglob("*.ndjson")):
        raw = p.read_bytes()
        if raw[:3] == codecs.BOM_UTF8:
            raw = raw[3:]
        text = raw.decode("utf-8", errors="replace")
        for line in io.StringIO(text).read().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            yield normalize(obj)


def rabbitmq_source(queue: str = RABBIT_QUEUE) -> Iterable[Dict]:
    credentials = pika.PlainCredentials(RABBIT_USER, RABBIT_PASS)
    parameters = pika.ConnectionParameters(
        host=RABBIT_HOST,
        port=RABBIT_PORT,
        credentials=credentials,
    )

    max_attempts = 50
    for attempt in range(max_attempts):
        try:
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            channel.queue_declare(queue=queue, durable=True)
            print(f"[BUILDER] Connected to RabbitMQ at {RABBIT_HOST}:{RABBIT_PORT}")
            break
        except pika.exceptions.AMQPConnectionError:
            print(
                f"[BUILDER] RabbitMQ not ready, retry {attempt+1}/{max_attempts}..."
            )
            time.sleep(2)
    else:
        raise Exception(
            f"[BUILDER] Cannot connect to RabbitMQ after {max_attempts} attempts"
        )

    try:
        for method_frame, properties, body in channel.consume(
            queue=queue, inactivity_timeout=1
        ):
            if body is None:
                continue
            try:
                data = json.loads(body.decode("utf-8"))
                yield normalize(data)
                channel.basic_ack(method_frame.delivery_tag)
            except Exception:
                continue
    finally:
        channel.cancel()
        connection.close()


def choose_source() -> Iterable[Dict]:
    if INGEST_SOURCE == "rabbitmq":
        return rabbitmq_source()
    if INGEST_SOURCE == "filesystem":
        return filesystem_source()
    raise ValueError(
        f"INGEST_SOURCE must be 'rabbitmq' or 'filesystem', got '{INGEST_SOURCE}'"
    )


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REJECT_DIR.mkdir(parents=True, exist_ok=True)
    print(
        f"[BUILDER] start mode={INGEST_SOURCE} OUT_DIR={OUT_DIR} RAW_DIR={RAW_DIR} "
        f"rabbit_host={RABBIT_HOST if INGEST_SOURCE=='rabbitmq' else None}"
    )

    src = choose_source()
    batch, t0 = [], time.time()

    try:
        for rec in src:
            batch.append(rec)
            now = time.time()

            if (now - t0) >= BATCH_MAX_SEC:
                try:
                    n = flush_batch(batch)
                    logger.info(
                        f"[BUILDER] batch_flushed batch_size={len(batch)} rows_written={n}"
                    )
                except Exception as e:
                    logger.error(f"[BUILDER] flush_failed error={e}")
                    n = 0
                batch.clear()
                t0 = now

    except KeyboardInterrupt:
        print("[BUILDER] shutdown_requested (KeyboardInterrupt)")
    finally:
        if batch:
            n = flush_batch(batch)
            print(
                f"[BUILDER] final_flush batch_size={len(batch)} rows_written={n}"
            )


if __name__ == "__main__":
    main()
