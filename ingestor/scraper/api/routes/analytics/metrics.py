from pathlib import Path
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from typing import Literal
from datetime import datetime
import duckdb
import glob
import os

from scraper.api.utils.json_api_res_template import JsonApiTemplate

router = APIRouter(prefix="/metrics", tags=["metrics"])

def _resolve_db_path() -> str:
    base_dir = Path(__file__).resolve().parents[3] 
    default_path = base_dir / "data" / "duck" / "warehouse.duckdb"
    return str(default_path.resolve(strict=False))

DB_FILE = _resolve_db_path()

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

@router.get("/latest")
def get_latest():
    database_error = ApiResponse._create_response(
        level="warning",
        msg=f"Database not found at {DB_FILE}",
        response={"updated_at": None, "counts": {}},
    )
    no_data_found = ApiResponse._create_response(
        level="info",
        msg="No data found",
        response={"updated_at": None, "counts": {}},
    )

    if not os.path.exists(DB_FILE):
        raise HTTPException(status_code=404, detail=database_error)

    with duckdb.connect(database=DB_FILE) as con:
        rows = con.execute("SELECT source, window_label, updated_at, count FROM latest").fetchall()

        if not rows:
            try:
                art_counts = con.execute("SELECT source, COUNT(*) FROM articles GROUP BY source").fetchall()
                counts = {r[0]: r[1] for r in art_counts}
                latest_ts = con.execute("SELECT MAX(fetched_at) FROM articles").fetchone()[0]
                snapshot = {
                    "updated_at": latest_ts.isoformat() if latest_ts is not None else None,
                    "counts": counts,
                }
                resp = ApiResponse._create_response(level="info", msg="Success (computed from articles)", response=snapshot)
                return JSONResponse(content=resp, status_code=200)
            except Exception:
                # If fallback fails, return consistent 404
                raise HTTPException(status_code=404, detail=no_data_found)

    # If we have rows in latest table, use them
    counts = {src: cnt for (src, _w, _ts, cnt) in rows}
    # Compute the latest timestamp among rows
    updated_values = [ts for (_s, _w, ts, _c) in rows if ts is not None]
    latest_ts = max(updated_values) if updated_values else None
    snapshot = {
        "updated_at": latest_ts.isoformat() if latest_ts is not None else None,
        "counts": counts,
    }
    resp = ApiResponse._create_response(level="info", msg="Success", response=snapshot)
    return JSONResponse(content=resp, status_code=200)


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
        LIMIT ?
    """

    with duckdb.connect(database=":memory:") as con:
        con.execute(query, [dt_from, dt_to, limit_int])
        rows = con.fetchall()

    result = [{"source": r[0], "value": r[1]} for r in rows]
    return JSONResponse(content=result, status_code=200)

@router.get("/aggregate")
def get_aggregate(to: str, bucket: Literal["day", "hour"], from_: str = Query(alias="from")):
    database_error = ApiResponse._create_response(level="warning", msg=f"Database not found at {DB_FILE}", response=[])
    no_data_found = ApiResponse._create_response(level="info", msg=f"Nothing found for the selected period", response=[])

    if not os.path.exists(DB_FILE):
        raise HTTPException(detail=no_data_found, status_code=404)
    else :
        with duckdb.connect(database=DB_FILE) as con:
            query = con.sql(f"SELECT * FROM articles WHERE fetched_at BETWEEN '{parse_datetime(from_)}' AND '{parse_datetime(to)}'").df()
            print(query)
            if len(query) == 0:
                con.close()
                raise HTTPException(detail=database_error, status_code=404)
            else:
                oldest = query.sort_values("ts").groupby("source").tail(1).copy()
                for col in oldest.select_dtypes(include=['datetime64', 'datetimetz']).columns:
                    oldest[col] = oldest[col].dt.strftime('%Y-%m-%d %H:%M:%S')
                oldest = oldest.to_dict(orient="records")

                latest = query.sort_values("ts").groupby("source").head(1).copy()
                for col in latest.select_dtypes(include=['datetime64', 'datetimetz']).columns:
                    latest[col] = latest[col].dt.strftime('%Y-%m-%d %H:%M:%S')
                latest = latest.to_dict(orient="records")
                
                count = query["symbol"].value_counts().to_dict()
                avg = query.groupby("symbol")["price_usd"].mean().to_dict()

                json_object = {
                    "oldest": oldest,
                    "latest": latest,
                    "count": count,
                    "avg": avg
                }
                con.close()
                datas = ApiResponse._create_response(level="info", msg=f"Datas found", response=json_object)
                return JSONResponse(content=datas, status_code=200)
