import os
from pathlib import Path

import fastapi
from fastapi import APIRouter
import sqlite3
from dotenv import load_dotenv

from ..utils import JsonApiTemplate

def _resolve(path: Path) -> Path:
    if path.is_absolute():
        return path
    return (Path.cwd() / path).resolve()

DB_PATH = _resolve(Path("component/scraperdb/data/ingestor.db"))

router = APIRouter(
    prefix="/symbols",
    tags=["symbols"]
)

ApiResponse = JsonApiTemplate("api")
con = sqlite3.connect(DB_PATH)

@router.get("/api/symbols")
async def get_symbols():
    try:
        cursor = con.cursor()
        symbols = cursor.execute("SELECT * FROM symbol")

        myResponse = ApiResponse._create_response(
            level="info",
            msg="Symbols list",
            response={
                "stauts": 200,
                "data": symbols
            }
        )

        return myResponse
    except Exception as e:
        myError = ApiResponse._create_response(
            level="error",
            msg="Error while fetching symbols",
            response={
                "status": 500,
                "error": str(e)
            }
        )
        return myError