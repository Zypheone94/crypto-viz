"""API server for the scraper."""
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="Crypto Viz Scraper API",
    description="API for the Crypto Viz Scraper",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

START_TIME = time.time()
LAST_WRITE_TIME: Optional[datetime] = None

class HealthResponse(BaseModel):
    status: str
    last_write_at: Optional[str] = None
    uptime: str

def get_last_write_time() -> Optional[datetime]:
    """Get the last write time by checking the most recent NDJSON file."""
    global LAST_WRITE_TIME
    
    # Default to parent directory data folder
    default_data_path = str(Path(__file__).parent.parent.parent / "data")
    data_path = Path(os.getenv("DATA_PATH", default_data_path))
    raw_path = data_path / "raw"
    
    if not raw_path.exists():
        return LAST_WRITE_TIME
    
    years = sorted([y for y in raw_path.glob("*") if y.is_dir()], reverse=True)
    if not years:
        return LAST_WRITE_TIME
    
    months = sorted([m for m in years[0].glob("*") if m.is_dir()], reverse=True)
    if not months:
        return LAST_WRITE_TIME
    
    days = sorted([d for d in months[0].glob("*") if d.is_dir()], reverse=True)
    if not days:
        return LAST_WRITE_TIME
    
    files = sorted([f for f in days[0].glob("*.ndjson") if f.is_file()], 
                  key=lambda f: f.stat().st_mtime, reverse=True)
    if not files:
        return LAST_WRITE_TIME
    
    LAST_WRITE_TIME = datetime.fromtimestamp(files[0].stat().st_mtime)
    return LAST_WRITE_TIME

@app.get("/health", response_model=HealthResponse)
async def health() -> Dict[str, Any]:
    """Health check endpoint."""
    uptime_seconds = time.time() - START_TIME
    uptime = str(timedelta(seconds=int(uptime_seconds)))
    
    last_write = get_last_write_time()
    
    return {
        "status": "ok",
        "last_write_at": last_write.isoformat() if last_write else None,
        "uptime": uptime,
    }

@app.get("/data/latest")
async def get_latest_data():
    """Get the latest scraped data."""
    raise HTTPException(status_code=501, detail="Not implemented yet")

@app.get("/data/export")
async def export_data():
    """Export all data."""
    raise HTTPException(status_code=501, detail="Not implemented yet")

def run_server():
    """Run the FastAPI server."""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("SCRAPER_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)