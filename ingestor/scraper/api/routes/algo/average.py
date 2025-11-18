from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import Literal, List, Dict, Any

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse

from ingestor.scraper.api.utils.json_api_res_template import JsonApiTemplate
from ingestor.builder.algo.average import (
    calculate_sma,
    calculate_wma,
    calculate_ema,
)


router = APIRouter(prefix="/algo", tags=["algo"])
ApiResponse = JsonApiTemplate("api")

DEFAULT_DB = "/app/ingestor/scraper/component/scraperdb/data/ingestor.db"
DB_PATH = os.getenv("FEEDER_DB_PATH", DEFAULT_DB)

ALLOWED_BUCKETS: set[str] = {"day", "hour"}
ALLOWED_MA: set[str] = {"sma", "wma", "ema", "all"}


def _parse_iso(dt_str: str, name: str) -> datetime:
    s = (dt_str or "").strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=ApiResponse._create_response(
                level="error", msg=f"Paramètre '{name}' invalide (ISO 8601)", response=[]
            ),
        )
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _pick_default_symbol(con: sqlite3.Connection) -> str | None:
    row = con.execute(
        "SELECT symbol, COUNT(*) AS c FROM article WHERE symbol IS NOT NULL GROUP BY symbol ORDER BY c DESC LIMIT 1"
    ).fetchone()
    return row[0] if row else None


def _load_bucketed_prices(
    con: sqlite3.Connection,
    symbol: str,
    dt_from: datetime,
    dt_to: datetime,
    bucket: Literal["day", "hour"],
) -> List[Dict[str, Any]]:
    """Return a list of {t, price} averaged per bucket for a given symbol.

    We normalize fetched_at strings into SQLite datetime and group by day/hour.
    """
    from_str = dt_from.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
    to_str = dt_to.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")

    if bucket == "hour":
        bucket_sql = "strftime('%Y-%m-%dT%H:00:00', datetime(replace(substr(fetched_at,1,19),'T',' ')))"
    else:
        bucket_sql = "strftime('%Y-%m-%dT00:00:00', datetime(replace(substr(fetched_at,1,19),'T',' ')))"

    sql = f"""
        SELECT {bucket_sql} AS t, AVG(price) AS price
        FROM article
        WHERE LOWER(symbol) = LOWER(?)
          AND price IS NOT NULL
          AND fetched_at IS NOT NULL
          AND datetime(replace(substr(fetched_at,1,19),'T',' ')) >= datetime(?)
          AND datetime(replace(substr(fetched_at,1,19),'T',' ')) <= datetime(?)
        GROUP BY t
        ORDER BY t ASC
    """

    rows = con.execute(sql, (symbol, from_str, to_str)).fetchall()
    return [{"t": r[0], "price": float(r[1])} for r in rows]


@router.get("/availability")
def availability(symbol: str | None = Query(None)):
    """Quick helper to inspect available symbols and their time ranges."""
    if not os.path.exists(DB_PATH):
        raise HTTPException(
            status_code=500,
            detail=ApiResponse._create_response(level="error", msg=f"Database not found at {DB_PATH}", response=[]),
        )
    try:
        con = sqlite3.connect(DB_PATH)
    except sqlite3.Error as e:
        raise HTTPException(
            status_code=500,
            detail=ApiResponse._create_response(level="error", msg=f"SQLite error: {e}", response=[]),
        )

    with con:
        params: list[Any] = []
        where = ""
        if symbol:
            where = "WHERE symbol = ?"
            params.append(symbol)
        rows = con.execute(
            f"""
            SELECT symbol,
                   COUNT(*) AS cnt,
                   MIN(datetime(replace(substr(fetched_at,1,19),'T',' '))) AS first_ts,
                   MAX(datetime(replace(substr(fetched_at,1,19),'T',' '))) AS last_ts
            FROM article
            {where}
            GROUP BY symbol
            ORDER BY cnt DESC
            """,
            params,
        ).fetchall()
    data = [
        {"symbol": r[0], "count": int(r[1]), "first_ts": r[2], "last_ts": r[3]} for r in rows
    ]
    return JSONResponse(
        content=ApiResponse._create_response(level="info", msg="Availability", response=data),
        status_code=200,
    )


@router.get("/moving-averages")
def moving_averages(
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
    window: int = Query(7, ge=2, le=365),
    ma_type: Literal["sma", "wma", "ema", "all"] = Query("sma"),
    bucket: Literal["day", "hour"] = Query("day"),
    symbol: str | None = Query(None, description="Crypto symbol (e.g., BTC). If omitted, the most frequent symbol is used."),
    limit: int = Query(10000, ge=10, le=100000, description="Max points to return after bucketing"),
):
    if bucket not in ALLOWED_BUCKETS:
        raise HTTPException(
            status_code=400,
            detail=ApiResponse._create_response(level="error", msg="bucket invalide (day|hour)", response=[]),
        )
    if ma_type not in ALLOWED_MA:
        raise HTTPException(
            status_code=400,
            detail=ApiResponse._create_response(level="error", msg="ma_type invalide (sma|wma|ema|all)", response=[]),
        )

    dt_from = _parse_iso(from_, "from")
    dt_to = _parse_iso(to, "to")
    if dt_from >= dt_to:
        raise HTTPException(
            status_code=400,
            detail=ApiResponse._create_response(level="error", msg="'from' doit être < 'to'", response=[]),
        )

    if not os.path.exists(DB_PATH):
        raise HTTPException(
            status_code=500,
            detail=ApiResponse._create_response(level="error", msg=f"Database not found at {DB_PATH}", response=[]),
        )

    try:
        con = sqlite3.connect(DB_PATH)
    except sqlite3.Error as e:
        raise HTTPException(
            status_code=500,
            detail=ApiResponse._create_response(level="error", msg=f"SQLite error: {e}", response=[]),
        )

    with con:
        chosen_symbol = symbol or _pick_default_symbol(con)
        if not chosen_symbol:
            return JSONResponse(
                status_code=200,
                content=ApiResponse._create_response(level="info", msg="No symbol found in DB", response=[]),
            )
        series = _load_bucketed_prices(con, chosen_symbol, dt_from, dt_to, bucket)

    if not series:
        return JSONResponse(
            status_code=200,
            content=ApiResponse._create_response(level="info", msg=f"No data for symbol {chosen_symbol} in range", response=[]),
        )

    if len(series) > limit:
        series = series[-limit:]

    ts = [p["t"] for p in series]
    values = [p["price"] for p in series]

    if len(values) < window:
        raise HTTPException(
            status_code=400,
            detail=ApiResponse._create_response(
                level="error", msg=f"Not enough points ({len(values)}) for window={window}", response=[]
            ),
        )

    types = [ma_type] if ma_type != "all" else ["sma", "wma", "ema"]

    result: Dict[str, Any] = {
        "symbol": chosen_symbol,
        "bucket": bucket,
        "window": window,
        "types": types,
        "count": len(values),
    }

    if "sma" in types:
        sma_vals = calculate_sma(values, window)
        result["sma"] = [{"t": ts[i + window - 1], "value": round(v, 6)} for i, v in enumerate(sma_vals)]

    if "wma" in types:
        wma_vals = calculate_wma(values, window)
        result["wma"] = [{"t": ts[i + window - 1], "value": round(v, 6)} for i, v in enumerate(wma_vals)]

    if "ema" in types:
        ema_vals = calculate_ema(values, window)
        result["ema"] = [{"t": ts[i + window - 1], "value": round(v, 6)} for i, v in enumerate(ema_vals)]

    payload = ApiResponse._create_response(level="info", msg="Success", response=result)
    return JSONResponse(content=payload, status_code=200)