"""Automated feeder that pulls cleaned parquet files into the SQLite warehouse."""

from __future__ import annotations

import logging
import os
import shutil
import sqlite3
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

LOGGER = logging.getLogger("database_feeder")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Charger les variables d environnement
load_dotenv()

# Configuration des chemins
OUT_DIR = Path(os.getenv("OUT_DIR", "/data/clean/parquet"))
DB_PATH = Path(os.getenv("FEEDER_DB_PATH", "/app/data/ingestor.db"))
DELTA_PARQUET_DIR = Path(os.getenv("DELTA_PARQUET_DIR", "/data/metrics/delta"))
REJECT_DIR = OUT_DIR.parent / "_corrupt"
RETAIN_DIR = OUT_DIR.parent / "_retained"
POLL_SECONDS = int(os.getenv("FEEDER_POLL_SECONDS", "60"))
RETAIN_MAX = max(int(os.getenv("FEEDER_RETAIN_FILES", "5")), 0)


def init_database() -> None:
    """Initialise la base de donnees avec les tables necessaires."""
    LOGGER.info("Initializing database at %s", DB_PATH)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    con = sqlite3.connect(DB_PATH)
    try:
        cur = con.cursor()
        
        # Table symbol
        cur.execute("""
        CREATE TABLE IF NOT EXISTS symbol (
            id INTEGER PRIMARY KEY,
            symbol TEXT UNIQUE NOT NULL
        );
        """)
        
        # Table article
        cur.execute("""
        CREATE TABLE IF NOT EXISTS article (
            id INTEGER PRIMARY KEY,
            fetched_at TIMESTAMP,
            url TEXT,
            symbol TEXT NOT NULL,
            name TEXT,
            price FLOAT,
            market_cap FLOAT,
            volume_24h FLOAT,
            coin_circulating FLOAT,
            FOREIGN KEY(symbol) REFERENCES symbol(symbol)
        );
        """)
        
        # Table delta
        cur.execute("""
        CREATE TABLE IF NOT EXISTS delta (
            id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL,
            date_start TIMESTAMP,
            date_end DATE,
            window_label TEXT,
            delta FLOAT,
            delta_pct FLOAT,
            FOREIGN KEY(symbol) REFERENCES symbol(symbol)
        );
        """)
        
        con.commit()
        LOGGER.info("Database initialized successfully")
        
        # Afficher les tables creees
        tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
        LOGGER.info("Tables in database: %s", [t[0] for t in tables])
        
    finally:
        con.close()


def find_parquet_files(base_dir: Path) -> list[Path]:
    """Trouve tous les fichiers parquet dans le repertoire."""
    if not base_dir.exists():
        LOGGER.warning("Directory does not exist: %s", base_dir)
        return []
    
    files = sorted(p for p in base_dir.rglob("*.parquet") if p.is_file())
    LOGGER.debug("Found %d parquet files in %s", len(files), base_dir)
    return files


def load_parquet(path: Path) -> pd.DataFrame | None:
    """Charge un fichier parquet."""
    try:
        df = pd.read_parquet(path)
        LOGGER.debug("Loaded %d rows from %s", len(df), path.name)
        return df
    except Exception as exc:
        LOGGER.error("Failed to read %s: %s", path, exc)
        return None


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise les colonnes du DataFrame pour correspondre au schema de la base."""
    # Convertir les noms de colonnes en minuscules
    df = df.rename(columns={c: c.lower() for c in df.columns})
    
    # Mapper les alias de colonnes
    aliases = {
        "link": "url",
        "price_usd": "price",
        "market_cap_usd": "market_cap",
        "marketcap": "market_cap",
        "marketCap": "market_cap",
        "volume_24h": "volume_24h",
        "circulating_supply": "coin_circulating",
        "circulating": "coin_circulating",
        "date": "fetched_at",
    }
    
    for original, target in aliases.items():
        if original in df.columns and target not in df.columns:
            df = df.rename(columns={original: target})
    
    # S assurer que toutes les colonnes requises existent
    required_cols = [
        "fetched_at", "url", "symbol", "name", 
        "price", "market_cap", "volume_24h", "coin_circulating"
    ]
    
    for col in required_cols:
        if col not in df.columns:
            df[col] = None
    
    # Convertir les colonnes numeriques
    numeric_cols = ["price", "market_cap", "coin_circulating", "volume_24h"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    
    return df[required_cols]


def insert_articles(cur: sqlite3.Cursor, df: pd.DataFrame) -> tuple[int, int]:
    """Insere les articles dans la base de donnees."""
    inserted = 0
    skipped = 0
    
    for _, row in df.iterrows():
        try:
            symbol = row.get("symbol")
            
            # Ignorer les lignes sans symbol
            if not symbol or pd.isna(symbol):
                skipped += 1
                continue
            
            # Inserer le symbol s il n existe pas
            cur.execute("INSERT OR IGNORE INTO symbol(symbol) VALUES (?)", (symbol,))
            
            # Inserer l article
            cur.execute("""
                INSERT INTO article(
                    fetched_at, url, symbol, name, 
                    price, market_cap, volume_24h, coin_circulating
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row.get("fetched_at"),
                row.get("url"),
                symbol,
                row.get("name"),
                row.get("price"),
                row.get("market_cap"),
                row.get("volume_24h"),
                row.get("coin_circulating"),
            ))
            
            inserted += 1
            
        except Exception as exc:
            LOGGER.error("Failed to insert row: %s", exc)
            skipped += 1
    
    return inserted, skipped


def ensure_dir(path: Path) -> None:
    """Cree un repertoire s il n existe pas."""
    path.mkdir(parents=True, exist_ok=True)


def move_to_reject(path: Path) -> None:
    """Deplace un fichier vers le repertoire des fichiers rejetes."""
    ensure_dir(REJECT_DIR)
    target = REJECT_DIR / path.name
    
    # Si le fichier existe deja, ajouter un timestamp
    if target.exists():
        timestamp = int(time.time())
        target = REJECT_DIR / f"{path.stem}_{timestamp}{path.suffix}"
    
    LOGGER.warning("Moving %s to %s", path.name, target)
    shutil.move(str(path), str(target))


def retain_file(path: Path) -> None:
    """Deplace un fichier vers le repertoire de retention ou le supprime."""
    if RETAIN_MAX <= 0:
        LOGGER.debug("Deleting %s (retention disabled)", path.name)
        path.unlink(missing_ok=True)
        cleanup_empty_dirs(path.parent)
        return
    
    # Deplacer vers le repertoire de retention
    relative = path.relative_to(OUT_DIR) if path.is_relative_to(OUT_DIR) else Path(path.name)
    target = RETAIN_DIR / relative
    
    ensure_dir(target.parent)
    shutil.move(str(path), str(target))
    LOGGER.debug("Retained %s", path.name)
    
    cleanup_empty_dirs(path.parent)
    prune_retained_files()


def cleanup_empty_dirs(path: Path) -> None:
    """Supprime les repertoires vides jusqu a OUT_DIR."""
    try:
        if path != OUT_DIR and path.exists() and not any(path.iterdir()):
            path.rmdir()
            LOGGER.debug("Removed empty directory %s", path)
            cleanup_empty_dirs(path.parent)
    except OSError:
        pass


def prune_retained_files() -> None:
    """Supprime les fichiers les plus anciens de la retention si necessaire."""
    if RETAIN_MAX <= 0 or not RETAIN_DIR.exists():
        return
    
    files = sorted(
        (p for p in RETAIN_DIR.rglob("*.parquet") if p.is_file()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    
    for stale in files[RETAIN_MAX:]:
        LOGGER.debug("Pruning old retained file %s", stale.name)
        stale.unlink(missing_ok=True)
        cleanup_empty_dirs(stale.parent)


def process_file(cur: sqlite3.Cursor, path: Path) -> tuple[int, int]:
    """Traite un fichier parquet."""
    LOGGER.info("Processing %s", path.name)
    
    # Charger le fichier
    df = load_parquet(path)
    if df is None:
        move_to_reject(path)
        return 0, 0
    
    # Verifier si le DataFrame est vide
    if df.empty:
        LOGGER.info("Skipping empty file %s", path.name)
        retain_file(path)
        return 0, 0
    
    # Normaliser le DataFrame
    try:
        normalized = normalize_dataframe(df)
    except Exception as exc:
        LOGGER.error("Failed to normalize %s: %s", path.name, exc)
        move_to_reject(path)
        return 0, 0
    
    # Inserer dans la base
    inserted, skipped = insert_articles(cur, normalized)
    LOGGER.info("File %s: inserted=%d skipped=%d", path.name, inserted, skipped)
    
    # Archiver le fichier
    retain_file(path)
    
    return inserted, skipped


def run_cycle() -> None:
    """Execute un cycle de traitement des fichiers parquet."""
    files = find_parquet_files(OUT_DIR)
    
    if not files:
        LOGGER.info("No parquet files found under %s", OUT_DIR)
        return
    
    LOGGER.info("Processing %d file(s) from %s", len(files), OUT_DIR)
    
    con = sqlite3.connect(DB_PATH)
    try:
        cur = con.cursor()
        total_inserted = 0
        total_skipped = 0
        
        for file_path in files:
            inserted, skipped = process_file(cur, file_path)
            total_inserted += inserted
            total_skipped += skipped
        
        con.commit()
        LOGGER.info("Cycle complete: inserted=%d skipped=%d", total_inserted, total_skipped)
        
    except Exception as exc:
        LOGGER.error("Error during cycle: %s", exc)
        con.rollback()
    finally:
        con.close()


def compute_deltas() -> None:
    """Calcule les deltas sur les prix des articles et les insere dans la table delta."""
    LOGGER.info("Computing deltas...")
    
    con = sqlite3.connect(DB_PATH)
    try:
        cur = con.cursor()
        
        # Recuperer les donnees par symbol et par fenetre de 10 minutes
        query = """
        WITH time_windows AS (
            SELECT 
                symbol,
                datetime(
                    substr(fetched_at, 1, 10) || ' ' || 
                    printf('%02d', (CAST(substr(fetched_at, 12, 2) AS INTEGER) * 60 + 
                                    CAST(substr(fetched_at, 15, 2) AS INTEGER)) / 10 * 10 / 60) || ':' ||
                    printf('%02d', (CAST(substr(fetched_at, 12, 2) AS INTEGER) * 60 + 
                                    CAST(substr(fetched_at, 15, 2) AS INTEGER)) / 10 * 10 % 60) || ':00'
                ) as window_start,
                AVG(price) as avg_price,
                COUNT(*) as count
            FROM article
            WHERE price IS NOT NULL AND fetched_at IS NOT NULL
            GROUP BY symbol, window_start
            HAVING count > 0
        ),
        windowed_with_prev AS (
            SELECT 
                symbol,
                window_start,
                datetime(window_start, '+10 minutes') as window_end,
                avg_price as price,
                LAG(avg_price) OVER (PARTITION BY symbol ORDER BY window_start) as prev_price
            FROM time_windows
        )
        SELECT 
            symbol,
            window_start,
            window_end,
            price,
            prev_price,
            (price - prev_price) as delta,
            CASE 
                WHEN prev_price IS NOT NULL AND prev_price != 0 
                THEN ((price - prev_price) / prev_price * 100.0)
                ELSE NULL
            END as delta_pct
        FROM windowed_with_prev
        WHERE prev_price IS NOT NULL
        """
        
        results = cur.execute(query).fetchall()
        
        if not results:
            LOGGER.info("No deltas to compute")
            return
        
        # Inserer les deltas
        inserted = 0
        for row in results:
            symbol, window_start, window_end, price, prev_price, delta, delta_pct = row
            
            # Verifier que le delta n'existe pas deja
            existing = cur.execute("""
                SELECT id FROM delta 
                WHERE symbol = ? AND date_start = ? AND date_end = ?
            """, (symbol, window_start, window_end)).fetchone()
            
            if existing:
                continue
            
            window_label = f"{symbol}_{window_start}_{window_end}"
            
            cur.execute("""
                INSERT INTO delta (symbol, date_start, date_end, window_label, delta, delta_pct)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (symbol, window_start, window_end, window_label, delta, delta_pct))
            
            inserted += 1
        
        con.commit()
        LOGGER.info(f"Inserted {inserted} new deltas")
        
    except Exception as exc:
        LOGGER.error(f"Failed to compute deltas: {exc}")
        con.rollback()
    finally:
        con.close()


def main() -> None:
    """Point d entree principal."""
    LOGGER.info("=" * 80)
    LOGGER.info("Database Feeder starting")
    LOGGER.info("OUT_DIR: %s", OUT_DIR)
    LOGGER.info("DB_PATH: %s", DB_PATH)
    LOGGER.info("POLL_SECONDS: %d", POLL_SECONDS)
    LOGGER.info("RETAIN_MAX: %d", RETAIN_MAX)
    LOGGER.info("=" * 80)
    
    # Initialiser la base de donnees
    init_database()
    
    # Calculer les deltas initiaux
    compute_deltas()
    
    # Boucle principale
    DELTA_INTERVAL = 600  # 10 minutes en secondes
    last_delta_time = time.time()
    
    try:
        while True:
            cycle_start = time.time()
            run_cycle()
            
            # Verifier si il faut calculer les deltas
            if time.time() - last_delta_time >= DELTA_INTERVAL:
                compute_deltas()
                last_delta_time = time.time()
            
            duration = time.time() - cycle_start
            sleep_time = max(0, POLL_SECONDS - duration)
            
            if sleep_time > 0:
                LOGGER.debug("Sleeping for %.1f seconds", sleep_time)
                time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        LOGGER.info("Shutdown requested")
    except Exception as exc:
        LOGGER.error("Fatal error: %s", exc)
        raise


if __name__ == "__main__":
    main()
