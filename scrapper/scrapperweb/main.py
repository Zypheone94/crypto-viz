from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
from typing import Literal, Optional
from datetime import datetime
import duckdb
import glob
import os


# Initialisation du FastAPI app par Val
app = FastAPI()

PARQUET_PATH = os.path.join(
    os.path.dirname(__file__), "../../data/clean/parquet/**/*.parquet"
)

def parse_datetime(dt_str: str) -> datetime:
    try:
        return datetime.fromisoformat(dt_str)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid datetime: {dt_str}")

@app.get("/metrics/timeseries")
def metrics_timeseries(
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
    bucket: Literal["hour", "day"] = Query(...)
):
    # Validation des paramètres
    dt_from = parse_datetime(from_)
    dt_to = parse_datetime(to)
    if dt_from > dt_to:
        raise HTTPException(status_code=400, detail="'from' doit être <= 'to'")
    if bucket not in {"hour", "day"}:
        raise HTTPException(status_code=400, detail="Bucket invalide")

    # Récupération des fichiers Parquet
    files = glob.glob(PARQUET_PATH, recursive=True)
    if not files:
        return JSONResponse(content=[], status_code=200)

    # Query DuckDB
    con = duckdb.connect(database=':memory:')
    con.execute(f"""
        SELECT 
            date_trunc('{bucket}', ts) AS t, 
            count(*) AS value
        FROM read_parquet({files})
        WHERE ts >= ? AND ts <= ?
        GROUP BY t
        ORDER BY t
    """, [dt_from, dt_to])
    rows = con.fetchall()
    result = [{"t": r[0].isoformat(), "value": r[1]} for r in rows]

    return JSONResponse(content=result, status_code=200)

    # Fin du code par Val