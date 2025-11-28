from __future__ import annotations

import os
import mysql.connector
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


def _pick_default_symbol(con: mysql.connector.MySQLConnection) -> str | None:
    cursor = con.cursor()
    cursor.execute(
        "SELECT symbol, COUNT(*) AS c FROM article WHERE symbol IS NOT NULL GROUP BY symbol ORDER BY c DESC LIMIT 1"
    )
    row = cursor.fetchone()
    cursor.close()
    return row[0] if row else None


def _load_bucketed_prices(
    con: mysql.connector.MySQLConnection,
    symbol: str,
    dt_from: datetime,
    dt_to: datetime,
    bucket: Literal["day", "hour"],
) -> List[Dict[str, Any]]:
    """Return a list of {t, price} averaged per bucket for a given symbol.

    We normalize fetched_at strings into MySQL datetime and group by day/hour.
    """
    from_str = dt_from.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
    to_str = dt_to.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")

    # Utiliser une approche sans STR_TO_DATE dans le SELECT pour éviter les problèmes de %
    if bucket == "hour":
        sql = """
            SELECT DATE_FORMAT(fetched_at, '%Y-%m-%dT%H:00:00') AS t, 
                   AVG(price) AS price
            FROM article
            WHERE LOWER(symbol) = LOWER(%s)
              AND price IS NOT NULL
              AND fetched_at IS NOT NULL
              AND fetched_at >= %s
              AND fetched_at <= %s
            GROUP BY t
            ORDER BY t ASC
        """
    else:
        sql = """
            SELECT DATE_FORMAT(fetched_at, '%Y-%m-%dT00:00:00') AS t, 
                   AVG(price) AS price
            FROM article
            WHERE LOWER(symbol) = LOWER(%s)
              AND price IS NOT NULL
              AND fetched_at IS NOT NULL
              AND fetched_at >= %s
              AND fetched_at <= %s
            GROUP BY t
            ORDER BY t ASC
        """

    cursor = con.cursor()
    cursor.execute(sql, (symbol, from_str, to_str))
    rows = cursor.fetchall()
    cursor.close()
    return [{"t": r[0], "price": float(r[1])} for r in rows]


@router.get("/availability")
def availability(symbol: str | None = Query(None)):
    """Quick helper to inspect available symbols and their time ranges."""
    try:
        con = mysql.connector.connect(
            host="host.docker.internal",
            user="ingestor_user",
            password="password123",
            database="ingestor"
        )
    except mysql.connector.Error as e:
        raise HTTPException(
            status_code=500,
            detail=ApiResponse._create_response(level="error", msg=f"MySQL error: {e}", response=[]),
        )

    cursor = con.cursor()
    params: list[Any] = []
    where = ""
    if symbol:
        where = "WHERE symbol = %s"
        params.append(symbol)
    
    query = """
        SELECT symbol,
               COUNT(*) AS cnt,
               MIN(fetched_at) AS first_ts,
               MAX(fetched_at) AS last_ts
        FROM article
        """ + where + """
        GROUP BY symbol
        ORDER BY cnt DESC
    """
    cursor.execute(query, params)
    rows = cursor.fetchall()
    cursor.close()
    con.close()
    
    data = [
        {"symbol": r[0], "count": int(r[1]), "first_ts": str(r[2]) if r[2] else None, "last_ts": str(r[3]) if r[3] else None} for r in rows
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

    try:
        con = mysql.connector.connect(
            host="host.docker.internal",
            user="ingestor_user",
            password="password123",
            database="ingestor"
        )
    except mysql.connector.Error as e:
        raise HTTPException(
            status_code=500,
            detail=ApiResponse._create_response(level="error", msg=f"MySQL error: {e}", response=[]),
        )

    chosen_symbol = symbol or _pick_default_symbol(con)
    if not chosen_symbol:
        con.close()
        return JSONResponse(
            status_code=200,
            content=ApiResponse._create_response(level="info", msg="No symbol found in DB", response=[]),
        )
    series = _load_bucketed_prices(con, chosen_symbol, dt_from, dt_to, bucket)
    con.close()

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