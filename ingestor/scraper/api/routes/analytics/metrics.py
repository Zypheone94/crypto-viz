from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from typing import Literal
from datetime import datetime
import duckdb
import glob
import os
from ingestor.scraper.api.utils import JsonApiTemplate

router = APIRouter(prefix="/metrics", tags=["metrics"])

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
        myResponse = ApiResponse._create_response(level="error", msg="'from' doit être <= 'to'", response=[])
        raise HTTPException(status_code=400, detail=myResponse)

    # Récupération des fichiers Parquet
    files = glob.glob(PARQUET_PATH, recursive=True)
    if not files:
        myResponse = ApiResponse._create_response(level="warning", msg="No data found", response=[])
        return JSONResponse(content=myResponse, status_code=200)

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
    myResponse = ApiResponse._create_response(level="info", msg="Success", response=result)
    return JSONResponse(content=myResponse, status_code=200)

@router.get("/aggregate")
def get_aggregate(to: str, bucket: Literal["day", "hour"] ,from_: str = Query(alias="from")):
    myResponse = ApiResponse._create_response(level="info", msg="Success", response={to, bucket, from_})
    return JSONResponse(content=myResponse, status_code=200)
