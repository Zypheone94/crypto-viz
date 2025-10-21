from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from typing import Literal
from datetime import datetime, timezone, timedelta
import duckdb
import glob
import os

from api.utils.duckdb_client import read_latest_snapshot
from ..utils import JsonApiTemplate

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

    # Récupération des fichiers Parquet
    files = glob.glob(PARQUET_PATH, recursive=True)
    if not files:
        # Contrat: renvoyer une liste vide si aucune donnée
        return JSONResponse(content=[], status_code=200)

    # Query DuckDB
    parquet_list = ", ".join(f"'{f}'" for f in files)
    query = f"""
        SELECT 
            date_trunc('{bucket}', ts) AS t,
            COUNT(*) AS count
        FROM read_parquet([{parquet_list}])
        WHERE ts >= ? AND ts <= ?
        GROUP BY t
        ORDER BY t ASC
    """

    params = [dt_from_utc.replace(tzinfo=None), dt_to_utc.replace(tzinfo=None)]

    with duckdb.connect(database=":memory:") as con:
        con.execute(query, params)
        rows = con.fetchall()

    result = [{"t": _iso_z(r[0]) if isinstance(r[0], datetime) else str(r[0]), "count": int(r[1])} for r in rows]
    result.sort(key=lambda x: x["t"])

    return JSONResponse(content=result, status_code=200)

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