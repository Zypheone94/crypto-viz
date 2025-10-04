from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from typing import Literal
from datetime import datetime
import duckdb
import glob
import os


router = APIRouter(prefix="/metrics", tags=["metrics"])

PARQUET_PATH = os.path.join(
    os.path.dirname(__file__), "../../data/clean/parquet/**/*.parquet"
)

def parse_datetime(dt_str: str) -> datetime:
    try:
        return datetime.fromisoformat(dt_str)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid datetime: {dt_str}")

@router.get("/timeseries")
def get_timeseries(
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
    bucket: Literal["hour", "day"] = Query(...)
):
    # Validation des paramètres
    dt_from = parse_datetime(from_)
    dt_to = parse_datetime(to)
    if dt_from > dt_to:
        raise HTTPException(status_code=400, detail="'from' doit être <= 'to'")

    # Récupération des fichiers Parquet
    files = glob.glob(PARQUET_PATH, recursive=True)
    if not files:
        return JSONResponse(content=[], status_code=200)

    # Query DuckDB
    con = duckdb.connect(database=':memory:')
    # Construire une liste de chemins correctement quotés
    parquet_list = ", ".join(f"'{f}'" for f in files)
    query = f"""
        SELECT 
            date_trunc('{bucket}', ts) AS t,
            count(*) AS value
        FROM read_parquet([{parquet_list}])
        WHERE ts >= ? AND ts <= ?
        GROUP BY t
        ORDER BY t
    """
    con.execute(query, [dt_from, dt_to])
    rows = con.fetchall()
    result = [{"t": r[0].isoformat(), "value": r[1]} for r in rows]
    return JSONResponse(content=result, status_code=200)


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

    # Validation spécifique du limit pour retourner un message 400 personnalisé
    try:
        limit_int = int(limit)
    except Exception:
        return JSONResponse(status_code=400, content={"erreur": "la limite doit être un entier positif"})
    if limit_int <= 0:
        return JSONResponse(status_code=400, content={"erreur": "la limite doit être un entier positif"})

    # Récupération des fichiers Parquet
    files = glob.glob(PARQUET_PATH, recursive=True)
    if not files:
        return JSONResponse(content=[], status_code=200)

    # Query DuckDB
    parquet_list = ", ".join(f"'{f}'" for f in files)
    query = f"""
        SELECT 
            source,
            COUNT(*) AS value
        FROM read_parquet([{parquet_list}])
        WHERE ts >= ? AND ts < ?
          AND source IS NOT NULL
        GROUP BY source
        ORDER BY value DESC
        LIMIT {limit_int}
    """

    with duckdb.connect(database=":memory:") as con:
        con.execute(query, [dt_from, dt_to])
        rows = con.fetchall()

    result = [{"source": r[0], "value": r[1]} for r in rows]
    return JSONResponse(content=result, status_code=200)