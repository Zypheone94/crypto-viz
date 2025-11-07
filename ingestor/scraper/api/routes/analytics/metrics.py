from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from typing import Literal
from datetime import datetime, timezone, timedelta
import sqlite3
import os
import logging

from scraper.api.utils.json_api_res_template import JsonApiTemplate
from scraper.api.utils.sqlite_client import get_connection, get_db_path

router = APIRouter(prefix="/metrics", tags=["metrics"])
logger = logging.getLogger(__name__)

PARQUET_PATH = os.path.join(
    os.path.dirname(__file__), "../../data/clean/parquet/**/*.parquet"
)

ApiResponse = JsonApiTemplate("api")


def parse_datetime(dt_str: str) -> datetime:
    try:
        return datetime.fromisoformat(dt_str)
    except Exception:
        myResponse = ApiResponse._create_response(level="error", msg=f"Invalid datetime: {dt_str}", response=[])
        raise HTTPException(status_code=400, detail=myResponse)


@router.get("/trending")
def get_trending(
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
    bucket: Literal["hour", "day"] = Query("hour"),
    limit: int = Query(5, ge=1, le=100)
):
    dt_from = parse_datetime(from_)
    dt_to = parse_datetime(to)
    if dt_from > dt_to:
        myResponse = ApiResponse._create_response(level="error", msg="'from' doit être <= 'to'", response=[])
        raise HTTPException(status_code=400, detail=myResponse)

    window_label = "1h" if bucket == "hour" else "1d"

    db_path = get_db_path()
    if not db_path.exists():
        myResponse = ApiResponse._create_response(level="warning", msg=f"Database not found at {db_path}", response=[])
        return JSONResponse(content=myResponse, status_code=200)

    # Query for trending symbols based on delta_pct
    query = """
        SELECT
            symbol,
            delta,
            delta_pct
        FROM delta
        WHERE window_label = ?
          AND date_start >= ?
          AND date_end <= ?
        ORDER BY delta_pct DESC, delta DESC
        LIMIT ?
    """
    try:
        con = get_connection(read_only=True)
        cur = con.cursor()
        rows = cur.execute(query, [window_label, dt_from, dt_to, int(limit)]).fetchall()
        con.close()
    except sqlite3.Error as e:
        logger.error(f"SQLite error: {e}")
        myResponse = ApiResponse._create_response(level="info", msg="No trending data yet", response=[])
        return JSONResponse(content=myResponse, status_code=200)

    result = [{"symbol": r[0], "delta": r[1], "delta_pct": r[2]} for r in rows]
    level = "info" if result else "warning"
    msg = "Success" if result else "No data found"
    myResponse = ApiResponse._create_response(level=level, msg=msg, response=result)
    return JSONResponse(content=myResponse, status_code=200)

ALLOWED_BUCKETS = {"hour", "day"}
MAX_WINDOW_DAYS = 180

def _parse_iso_to_utc(dt_str: str, param_name: str) -> datetime:
    if not isinstance(dt_str, str):
        raise ValueError(f"Paramètre '{param_name}' invalide: chaîne ISO 8601 attendue")
    s = dt_str.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except Exception:
        raise ValueError(
            f"Paramètre '{param_name}' invalide: format ISO 8601 attendu (ex: 2025-09-18T10:00:00Z)"
        )
    if dt.tzinfo is None:
        raise ValueError(f"Paramètre '{param_name}' doit inclure un fuseau horaire (ex: suffixe 'Z')")
    return dt.astimezone(timezone.utc)

def _iso_z(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    s = dt.replace(microsecond=0).isoformat()
    if s.endswith("+00:00"):
        s = s[:-6] + "Z"
    return s

@router.get("/timeseries")
def get_timeseries(
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
    bucket: str = Query("day"), 
):
    # Validation stricte des paramètres
    try:
        if bucket not in ALLOWED_BUCKETS:
            return JSONResponse(status_code=400, content={"error": "bucket invalide: doit être 'hour' ou 'day'"})

        dt_from_utc = _parse_iso_to_utc(from_, "from")
        dt_to_utc = _parse_iso_to_utc(to, "to")

        if not (dt_from_utc < dt_to_utc):
            return JSONResponse(status_code=400, content={"error": "'from' doit être strictement inférieur à 'to'"})

        if (dt_to_utc - dt_from_utc) > timedelta(days=MAX_WINDOW_DAYS):
            return JSONResponse(status_code=400, content={"error": f"fenêtre maximale de {MAX_WINDOW_DAYS} jours dépassée"})
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

    # Query SQLite for articles in time range
    # Using strftime for date bucketing
    bucket_format = '%Y-%m-%d' if bucket == 'day' else '%Y-%m-%d %H:00:00'
    
    query = """
        SELECT 
            strftime(?, date) AS t,
            COUNT(*) AS count
        FROM article
        WHERE date >= ? AND date <= ?
        GROUP BY t
        ORDER BY t ASC
    """

    try:
        con = get_connection(read_only=True)
        cur = con.cursor()
        rows = cur.execute(query, [bucket_format, dt_from_utc.replace(tzinfo=None), dt_to_utc.replace(tzinfo=None)]).fetchall()
        con.close()
    except sqlite3.Error as e:
        logger.error(f"SQLite error: {e}")
        return JSONResponse(content=[], status_code=200)

    result = [{"t": str(r[0]), "count": int(r[1])} for r in rows]
    result.sort(key=lambda x: x["t"])

    return JSONResponse(content=result, status_code=200)

def read_latest_snapshot():
    """Get the latest article from the database."""
    query = """
        SELECT date, source, symbol, price, titre, url
        FROM article
        ORDER BY date DESC
        LIMIT 1
    """
    try:
        con = get_connection(read_only=True)
        cur = con.cursor()
        rows = cur.execute(query).fetchall()
        con.close()
        
        if rows:
            return [{
                "date": str(rows[0][0]),
                "source": rows[0][1],
                "symbol": rows[0][2],
                "price": rows[0][3],
                "titre": rows[0][4],
                "url": rows[0][5]
            }]
    except sqlite3.Error as e:
        logger.error(f"SQLite error: {e}")
    
    return []

@router.get("/latest")
def get_latest():
    snapshot = read_latest_snapshot()
    return JSONResponse(content=snapshot, status_code=200)


@router.get("/top")
def get_top(
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
    limit: int = Query(10)
):

    # Validation des paramètres
    dt_from = parse_datetime(from_)
    dt_to = parse_datetime(to)
    if dt_from > dt_to:
        raise HTTPException(status_code=400, detail="'from' doit être <= 'to'")

    # Validation spécifique du limit pour retourner un message 400
    try:
        limit_int = int(limit)
    except Exception:
        return JSONResponse(status_code=400, content={"erreur": "la limite doit être un entier positif"})
    if limit_int <= 0:
        return JSONResponse(status_code=400, content={"erreur": "la limite doit être un entier positif"})

    # Query SQLite for top sources by article count
    query = """
        SELECT 
            source,
            COUNT(*) AS value
        FROM article
        WHERE date >= ? AND date < ?
          AND source IS NOT NULL
        GROUP BY source
        ORDER BY value DESC
        LIMIT ?
    """

    try:
        con = get_connection(read_only=True)
        cur = con.cursor()
        rows = cur.execute(query, [dt_from, dt_to, limit_int]).fetchall()
        con.close()
    except sqlite3.Error as e:
        logger.error(f"SQLite error: {e}")
        return JSONResponse(content=[], status_code=200)

    result = [{"source": r[0], "value": r[1]} for r in rows]
    return JSONResponse(content=result, status_code=200)

@router.get("/aggregate")
def get_aggregate(to: str, bucket: Literal["day", "hour"], from_: str = Query(alias="from")):
    db_path = get_db_path()
    database_error = ApiResponse._create_response(level="warning", msg=f"Database not found at {db_path}", response=[])
    no_data_found = ApiResponse._create_response(level="info", msg=f"Nothing found for the selected period", response=[])

    if not db_path.exists():
        raise HTTPException(detail=database_error, status_code=404)
    
    dt_from = parse_datetime(from_)
    dt_to = parse_datetime(to)
    
    try:
        con = get_connection(read_only=True)
        cur = con.cursor()
        
        # Get articles in the time range
        query = """
            SELECT date, source, symbol, price, titre, url, name, market_cap, coin_circulating
            FROM article
            WHERE date BETWEEN ? AND ?
            ORDER BY date
        """
        rows = cur.execute(query, [dt_from, dt_to]).fetchall()
        
        if not rows:
            con.close()
            raise HTTPException(detail=no_data_found, status_code=404)
        
        # Convert to list of dicts
        articles = []
        for row in rows:
            articles.append({
                "date": str(row[0]),
                "source": row[1],
                "symbol": row[2],
                "price": row[3],
                "titre": row[4],
                "url": row[5],
                "name": row[6],
                "market_cap": row[7],
                "coin_circulating": row[8]
            })
        
        # Sort and group by source
        articles_sorted = sorted(articles, key=lambda x: x["date"])
        
        # Get oldest and latest by source
        sources = {}
        for article in articles_sorted:
            src = article["source"]
            if src not in sources:
                sources[src] = {"oldest": article, "latest": article}
            else:
                sources[src]["latest"] = article
        
        oldest = [v["oldest"] for v in sources.values()]
        latest = [v["latest"] for v in sources.values()]
        
        # Count by symbol
        symbol_counts = {}
        symbol_prices = {}
        for article in articles:
            sym = article["symbol"]
            symbol_counts[sym] = symbol_counts.get(sym, 0) + 1
            if sym not in symbol_prices:
                symbol_prices[sym] = []
            if article["price"] is not None:
                symbol_prices[sym].append(article["price"])
        
        # Calculate averages
        avg = {}
        for sym, prices in symbol_prices.items():
            if prices:
                avg[sym] = sum(prices) / len(prices)
        
        json_object = {
            "oldest": oldest,
            "latest": latest,
            "count": symbol_counts,
            "avg": avg
        }
        
        con.close()
        datas = ApiResponse._create_response(level="info", msg=f"Datas found", response=json_object)
        return JSONResponse(content=datas, status_code=200)
        
    except sqlite3.Error as e:
        logger.error(f"SQLite error: {e}")
        raise HTTPException(detail=database_error, status_code=500)
