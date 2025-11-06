import os, time, json, hashlib, pathlib, io, codecs, re, tempfile, shutil
from typing import Iterable, Dict, List, Set
from loguru import logger
import polars as pl
from dotenv import load_dotenv

def _clean_text(s: str | None) -> str | None:
    if s is None:
        return None
    s = s.encode("utf-8", errors="ignore").decode("utf-8")
    s = re.sub(r"\s+", " ", s.strip())
    return s

def _id(article: Dict) -> str:
    return hashlib.sha1(
        ((article.get("url") or "") + (article.get("title") or "")).encode("utf-8")
    ).hexdigest()



HERE = pathlib.Path(__file__).resolve().parent
load_dotenv("./.env")

OUT_DIR = pathlib.Path(os.getenv("OUT_DIR", "../data/clean/parquet"))
RAW_DIR = pathlib.Path(os.getenv("RAW_DIR", "../data/raw"))
REJECT_DIR = OUT_DIR.parent / "_corrupt"

INGEST_SOURCE = os.getenv("INGEST_SOURCE", "kafka").lower()
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "127.0.0.1:2111")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "crypto-viz")
BATCH_MAX_MSG = int(os.getenv("BATCH_MAX_MSG", "200"))
BATCH_MAX_SEC = int(os.getenv("BATCH_MAX_SEC", "5"))

SLEEP_SEC = int(os.getenv("BUILDER_POLL_INTERVAL", "5"))

SEEN_IDS: set[str] = set()


SYMBOLS_PARQUET = pathlib.Path(
    os.getenv("SYMBOLS_PARQUET", OUT_DIR / "symbols" / "symbols.parquet")
)
SYMBOLS_BATCH_SIZE = int(os.getenv("SYMBOLS_BATCH_SIZE", "200"))
SYMBOLS_FLUSH_SECS = float(os.getenv("SYMBOLS_FLUSH_SECS", "15.0"))

_SYMBOLS_BUFFER: Set[str] = set()
_LAST_SYMBOLS_FLUSH_MONO = time.monotonic()
_SYMBOL_CLEAN_RE = re.compile(r"[\s]")

def _ensure_parent_dir(p: pathlib.Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)

def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())

def _normalize_symbol(s: str | None) -> str | None:
    """
    Normalisation simple :
    - trim, upper
    - supprime espaces
    - remplace séparateurs courants par '/'
    """
    if not s:
        return None
    s = str(s).strip().upper()
    s = _SYMBOL_CLEAN_RE.sub("", s)
    s = s.replace("-", "/").replace("_", "/").replace(":", "/")
    return s

def _extract_symbols_from_record(rec: Dict) -> List[str]:
    out: List[str] = []

    sym = rec.get("symbol") or rec.get("ticker") or rec.get("pair")
    if sym:
        ns = _normalize_symbol(sym)
        if ns:
            out.append(ns)

    base, quote = rec.get("base"), rec.get("quote")
    if base and quote:
        ns = _normalize_symbol(f"{base}/{quote}")
        if ns:
            out.append(ns)

    syms = rec.get("symbols") or rec.get("tickers")
    if isinstance(syms, list):
        for s in syms:
            ns = _normalize_symbol(s)
            if ns:
                out.append(ns)
    return list(dict.fromkeys(out))

def _load_existing_symbols_df() -> pl.DataFrame:
    if SYMBOLS_PARQUET.exists():
        try:
            return pl.read_parquet(SYMBOLS_PARQUET)
        except Exception as e:
            logger.warning(f"[symbols] Lecture échouée {SYMBOLS_PARQUET}: {e}")
    return pl.DataFrame({"symbol": pl.Series([], pl.Utf8), "first_seen_at": pl.Series([], pl.Utf8)})

def _persist_symbols(new_syms: Set[str]) -> None:
    if not new_syms:
        return

    _ensure_parent_dir(SYMBOLS_PARQUET)

    existing = _load_existing_symbols_df()
    existing_syms = set(existing["symbol"].to_list()) if existing.height > 0 else set()

    really_new = sorted(s for s in new_syms if s not in existing_syms)
    if not really_new:
        return

    now_iso = _now_iso()
    df_new = pl.DataFrame(
        {
            "symbol": really_new,
            "first_seen_at": [now_iso] * len(really_new),
        }
    )

    combined = (
        (pl.concat([existing, df_new]) if existing.height > 0 else df_new)
        .unique(subset=["symbol"], keep="first")
        .sort("symbol")
    )

    _ensure_parent_dir(SYMBOLS_PARQUET)
    fd, tmp_path = tempfile.mkstemp(prefix="symbols_", suffix=".parquet", dir=str(SYMBOLS_PARQUET.parent))
    os.close(fd)
    tmp_path = pathlib.Path(tmp_path)

    try:
        combined.write_parquet(tmp_path, compression="zstd", use_pyarrow=False)
        shutil.move(str(tmp_path), str(SYMBOLS_PARQUET))
        logger.info(
            json.dumps(
                {
                    "service": "builder",
                    "msg": "symbols_parquet_written",
                    "added": len(really_new),
                    "total": int(combined.height),
                    "path": str(SYMBOLS_PARQUET),
                }
            )
        )
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)

def _maybe_flush_symbols(force: bool = False) -> None:
    global _LAST_SYMBOLS_FLUSH_MONO, _SYMBOLS_BUFFER
    now = time.monotonic()
    if force or len(_SYMBOLS_BUFFER) >= SYMBOLS_BATCH_SIZE or (now - _LAST_SYMBOLS_FLUSH_MONO) >= SYMBOLS_FLUSH_SECS:
        if _SYMBOLS_BUFFER:
            _persist_symbols(_SYMBOLS_BUFFER)
            _SYMBOLS_BUFFER.clear()
        _LAST_SYMBOLS_FLUSH_MONO = now



def normalize(a: Dict) -> Dict:
    return {
        "id": a.get("id") or _id(a),
        "title": a.get("title"),
        "published_at": a.get("published_at"),
        "url": a.get("url"),
        "source": a.get("source"),
        "symbol": a.get("symbol"),
        "name": a.get("name"),

        "price_usd": a.get("price_usd") or a.get("price"),
        "market_cap_usd": a.get("market_cap_usd") or a.get("market_cap"),

        "coin_circulating": (
            a.get("coin_circulating")
            or a.get("circulating_supply")
            or a.get("circulating")
        ),

        "fetched_at": a.get("fetched_at"),
        "base": a.get("base"),
        "quote": a.get("quote"),
        "symbols": a.get("symbols"),
        "tickers": a.get("tickers"),
        "pair": a.get("pair"),
        "ticker": a.get("ticker"),
    }




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
              "symbol","name","price_usd","market_cap_usd",
              "coin_circulating",
              "_corrupt_record"
          ])
    )
    valid = df.filter(pl.col("ts").is_not_null())

    valid = (
        valid.with_columns([
            pl.col("title").map_elements(_clean_text, return_dtype=pl.Utf8).alias("title"),
            pl.col("url").cast(pl.Utf8).map_elements(_clean_text, return_dtype=pl.Utf8).alias("url"),
            pl.col("source").cast(pl.Utf8).map_elements(_clean_text, return_dtype=pl.Utf8).alias("source"),
            pl.col("symbol").cast(pl.Utf8).map_elements(_clean_text, return_dtype=pl.Utf8).alias("symbol"),
            pl.col("name").cast(pl.Utf8).map_elements(_clean_text, return_dtype=pl.Utf8).alias("name"),

            pl.col("price_usd").cast(pl.Float64).alias("price_usd"),
            pl.col("market_cap_usd").cast(pl.Float64).alias("market_cap_usd"),
            pl.col("coin_circulating").cast(pl.Float64).alias("coin_circulating"),

            pl.col("ts").dt.date().alias("date"),
        ])
        .rename({
            "title": "titre",
            "price_usd": "price",
            "market_cap_usd": "market_cap",
        })
        .select([
            pl.col("id").cast(pl.Utf8),
            pl.col("date").cast(pl.Date),
            pl.col("titre").cast(pl.Utf8),
            pl.col("url").cast(pl.Utf8),
            pl.col("source").cast(pl.Utf8),
            pl.col("symbol").cast(pl.Utf8),
            pl.col("name").cast(pl.Utf8),
            pl.col("price").cast(pl.Float64),
            pl.col("market_cap").cast(pl.Float64),
            pl.col("coin_circulating").cast(pl.Float64),
        ])
    )

    if invalid.height > 0:
        REJECT_DIR.mkdir(parents=True, exist_ok=True)
        rej_path = REJECT_DIR / f"reject-{int(time.time())}.ndjson"
        with open(rej_path, "w", encoding="utf-8") as f:
            for rec in invalid.to_dicts():
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        logger.warning(json.dumps({
            "service": "builder", "mode": INGEST_SOURCE, "msg": "corrupt_rows",
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
            "service": "builder", "mode": INGEST_SOURCE, "msg": "parquet_written",
            "date": folder, "rows": g.height, "path": str(outpath)
        }))
        written += g.height

    return written

def kafka_source() -> Iterable[Dict]:
    from kafka import KafkaConsumer
    c = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=[KAFKA_BOOTSTRAP],
        client_id=os.getenv("KAFKA_CLIENT_ID", "builder-consumer"),
        group_id=os.getenv("KAFKA_GROUP_ID", "builder-group"),
        security_protocol=os.getenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT"),
        enable_auto_commit=True,
        auto_offset_reset="latest",
        api_version=(3, 7, 0),
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        request_timeout_ms=int(os.getenv("KAFKA_REQUEST_TIMEOUT_MS", "15000")),
        session_timeout_ms=int(os.getenv("KAFKA_SESSION_TIMEOUT_MS", "10000")),
        metadata_max_age_ms=int(os.getenv("KAFKA_METADATA_MAX_AGE_MS", "30000")),
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
    logger.info(json.dumps({
        "service":"builder","msg":"consumer_start","mode":INGEST_SOURCE,
        "kafka_bootstrap":KAFKA_BOOTSTRAP if INGEST_SOURCE=='kafka' else None,
        "topic":KAFKA_TOPIC if INGEST_SOURCE=='kafka' else None,
        "raw_dir": str(RAW_DIR.resolve()) if INGEST_SOURCE=='filesystem' else None,
        "symbols_parquet": str(SYMBOLS_PARQUET),
        "symbols_batch_size": SYMBOLS_BATCH_SIZE,
        "symbols_flush_secs": SYMBOLS_FLUSH_SECS,
    }))

    src = choose_source()
    batch, t0 = [], time.time()

    try:
        for rec in src:
            try:
                syms = _extract_symbols_from_record(rec)
                if syms:
                    _SYMBOLS_BUFFER.update(syms)
                    _maybe_flush_symbols()
            except Exception as e:
                logger.warning(f"[symbols] Extraction ignorée: {e}")

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
        _maybe_flush_symbols(force=True)

if __name__ == "__main__":
    main()
