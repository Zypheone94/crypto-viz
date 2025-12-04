from pathlib import Path

import mysql.connector
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

import fastapi
import mysql
from fastapi import APIRouter
import sqlite3
from dotenv import load_dotenv

from ..utils import JsonApiTemplate

def _resolve(path: Path) -> Path:
    if path.is_absolute():
        return path
    return (Path.cwd() / path).resolve()

def db_connect():
    try:
        con = mysql.connector.connect(
            host="host.docker.internal",
            user="ingestor_user",
            password="password123",
            database="ingestor")
        print("Connected to database")
        return con
    except mysql.connector.Error as err:
        print("Could not connect to database : ", err)
        return None

router = APIRouter(
    prefix="/api",
    tags=["symbols"]
)

ApiResponse = JsonApiTemplate("api")
con = db_connect()

@router.get("/symbols")
async def get_symbols():
    """
    Retourne la liste de tous les symboles disponibles dans la base de données.
    """
    try:
        con = mysql.connector.connect(
            host="host.docker.internal",
            user="ingestor_user",
            password="password123",
            database="ingestor"
        )
        
        cursor = con.cursor()
        cursor.execute("SELECT symbol FROM symbol")
        symbols = [s[0] for s in cursor.fetchall()]

        return JSONResponse(
            content=ApiResponse._create_response(
                level="info",
                msg="Symbols retrieved successfully",
                response=symbols
            ),
            status_code=200
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=ApiResponse._create_response(
                level="error",
                msg=f"Error while fetching symbols: {str(e)}",
                response=[]
            )
        )