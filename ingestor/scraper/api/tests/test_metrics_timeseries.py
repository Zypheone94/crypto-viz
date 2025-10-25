import os
import sys
import types
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.testclient import TestClient

_HERE = os.path.dirname(__file__)
_PROJECT_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", "..")) 
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from scraper.api.routes.metrics import router as metrics_router

def make_app():
    app = FastAPI()
    app.include_router(metrics_router)
    return app

class DuckDBStub:
    def __init__(self, rows):
        self._rows = rows
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False
    def execute(self, query, params):
        self._last_query = query
        self._last_params = params
        return self
    def fetchall(self):
        return self._rows

def test_timeseries_day_success(monkeypatch):
    monkeypatch.setattr("ingestor.scraper.api.routes.metrics.glob.glob", lambda p, recursive=True: ["a.parquet"])

    rows = [
        (datetime(2025, 9, 18, 0, 0, 0), 5),
        (datetime(2025, 9, 19, 0, 0, 0), 3),
    ]
    monkeypatch.setattr("ingestor.scraper.api.routes.metrics.duckdb.connect", lambda database=":memory:": DuckDBStub(rows))

    app = make_app()
    client = TestClient(app)
    resp = client.get("/metrics/timeseries", params={
        "from": "2025-09-18T00:00:00Z",
        "to": "2025-09-20T00:00:00Z",
        "bucket": "day",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert data == [
        {"t": "2025-09-18T00:00:00Z", "count": 5},
        {"t": "2025-09-19T00:00:00Z", "count": 3},
    ]
    assert data == sorted(data, key=lambda x: x["t"])


def test_timeseries_hour_success(monkeypatch):
    monkeypatch.setattr("ingestor.scraper.api.routes.metrics.glob.glob", lambda p, recursive=True: ["a.parquet"])
    rows = [
        (datetime(2025, 9, 18, 11, 0, 0, tzinfo=timezone.utc), 2),
        (datetime(2025, 9, 18, 10, 0, 0, tzinfo=timezone.utc), 4),
    ]
    monkeypatch.setattr("ingestor.scraper.api.routes.metrics.duckdb.connect", lambda database=":memory:": DuckDBStub(rows))

    app = make_app()
    client = TestClient(app)
    resp = client.get("/metrics/timeseries", params={
        "from": "2025-09-18T09:00:00Z",
        "to": "2025-09-18T12:00:00Z",
        "bucket": "hour",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert [p["t"] for p in data] == ["2025-09-18T10:00:00Z", "2025-09-18T11:00:00Z"]
    assert all(p["t"].endswith("Z") for p in data)
    assert all(isinstance(p["count"], int) for p in data)


def test_timeseries_invalid_bucket():
    app = make_app()
    client = TestClient(app)
    resp = client.get("/metrics/timeseries", params={
        "from": "2025-09-18T10:00:00Z",
        "to": "2025-09-19T10:00:00Z",
        "bucket": "minute",
    })
    assert resp.status_code == 400
    assert resp.json() == {"error": "bucket invalide: doit être 'hour' ou 'day'"}


def test_timeseries_bad_format_tz_missing():
    app = make_app()
    client = TestClient(app)
    resp = client.get("/metrics/timeseries", params={
        "from": "2025-09-18T10:00:00",
        "to": "2025-09-19T10:00:00Z",
    })
    assert resp.status_code == 400
    assert "doit inclure un fuseau horaire" in resp.json()["error"]


def test_timeseries_from_ge_to():
    app = make_app()
    client = TestClient(app)
    resp = client.get("/metrics/timeseries", params={
        "from": "2025-09-18T10:00:00Z",
        "to": "2025-09-18T10:00:00Z",
    })
    assert resp.status_code == 400
    assert resp.json() == {"error": "'from' doit être strictement inférieur à 'to'"}


def test_timeseries_window_too_large():
    app = make_app()
    client = TestClient(app)
    resp = client.get("/metrics/timeseries", params={
        "from": "2025-01-01T00:00:00Z",
        "to": "2025-08-01T00:00:00Z",  # > 180 days
    })
    assert resp.status_code == 400
    assert "fenêtre maximale de" in resp.json()["error"]
