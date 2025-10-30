from pathlib import Path
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from typing import Literal
from datetime import datetime, timezone, timedelta
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

    if not os.path.exists(DB_FILE):
        myResponse = ApiResponse._create_response(level="warning", msg=f"Database not found at {DB_FILE}", response=[])
        return JSONResponse(content=myResponse, status_code=200)

    query = """
        SELECT
            source,
            value,
            delta_pct
        FROM metrics_trending
        WHERE window_label = ?
          AND as_of >= ?
          AND as_of <= ?
        ORDER BY delta_pct DESC NULLS LAST, value DESC
        LIMIT ?
    """
    try:
        with duckdb.connect(database=DB_FILE, read_only=True) as con:
            rows = con.execute(query, [window_label, dt_from, dt_to, int(limit)]).fetchall()
    except duckdb.CatalogException:
        myResponse = ApiResponse._create_response(level="info", msg="No trending data yet", response=[])
        return JSONResponse(content=myResponse, status_code=200)

    result = [{"source": r[0], "value": r[1], "delta_pct": r[2]} for r in rows]
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

def read_latest_snapshot():
    files = glob.glob(PARQUET_PATH, recursive=True)
    if not files:
        return []
    parquet_list = ", ".join(f"'{f}'" for f in files)
    query = f"""
        SELECT *
        FROM read_parquet([{parquet_list}])
        ORDER BY ts DESC
        LIMIT 1
    """
    with duckdb.connect(database=":memory:") as con:
        con.execute(query)
        rows = con.fetchall()
    if rows:
        columns = ["ts", "source", "symbol", "price_usd"]
        return [dict(zip(columns, row)) for row in rows]
    return []

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
          
                raise HTTPException(status_code=404, detail=no_data_found)

    counts = {src: cnt for (src, _w, _ts, cnt) in rows}

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
