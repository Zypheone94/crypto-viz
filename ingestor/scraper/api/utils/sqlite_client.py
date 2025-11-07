"""SQLite helper utilities for the metrics API.

This module maintains a SQLite database (`ingestor.db`) for storing and querying
crypto metrics data from the scraped articles.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def get_db_path() -> Path:
    """Get the path to the SQLite database."""
    base_dir = Path(__file__).resolve().parents[3]
    return base_dir / "scraper" / "component" / "scraperdb" / "data" / "ingestor.db"


def get_connection(read_only: bool = False) -> sqlite3.Connection:
    """Get a connection to the SQLite database.
    
    Args:
        read_only: If True, open database in read-only mode
        
    Returns:
        SQLite connection object
    """
    db_path = get_db_path()
    
    if not db_path.exists():
        logger.warning(f"Database not found at {db_path}")
        # Create parent directory if needed
        db_path.parent.mkdir(parents=True, exist_ok=True)
        # Initialize the database
        _initialize_database(db_path)
    
    uri = f"file:{db_path}?mode=ro" if read_only else str(db_path)
    con = sqlite3.connect(uri, uri=read_only)
    con.row_factory = sqlite3.Row  # Enable column access by name
    return con


def _initialize_database(db_path: Path) -> None:
    """Initialize the database with required tables."""
    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    
    cur.execute('''
    CREATE TABLE IF NOT EXISTS symbol (
        id INTEGER PRIMARY KEY,
        symbol TEXT UNIQUE NOT NULL
    );
    ''')
    
    cur.execute('''
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
    ''')
    
    cur.execute('''
    CREATE TABLE IF NOT EXISTS article (
        id INTEGER PRIMARY KEY,
        date DATE,
        titre TEXT,
        url TEXT,
        source TEXT,
        symbol TEXT NOT NULL,
        name TEXT,
        price FLOAT,
        market_cap FLOAT,
        coin_circulating FLOAT,
        FOREIGN KEY(symbol) REFERENCES symbol(symbol)
    );
    ''')
    
    # Create indexes for better query performance
    cur.execute('CREATE INDEX IF NOT EXISTS idx_article_date ON article(date);')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_article_symbol ON article(symbol);')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_article_source ON article(source);')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_delta_symbol ON delta(symbol);')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_delta_date ON delta(date_start, date_end);')
    
    con.commit()
    con.close()
    logger.info(f"Database initialized at {db_path}")


def execute_query(query: str, params: Optional[tuple] = None, read_only: bool = True) -> list:
    """Execute a query and return results.
    
    Args:
        query: SQL query string
        params: Query parameters (optional)
        read_only: If True, use read-only connection
        
    Returns:
        List of result rows
    """
    con = get_connection(read_only=read_only)
    try:
        cur = con.cursor()
        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)
        results = cur.fetchall()
        return results
    finally:
        con.close()


def execute_many(query: str, data: list[tuple]) -> None:
    """Execute a query with multiple parameter sets.
    
    Args:
        query: SQL query string
        data: List of parameter tuples
    """
    con = get_connection(read_only=False)
    try:
        cur = con.cursor()
        cur.executemany(query, data)
        con.commit()
    finally:
        con.close()
