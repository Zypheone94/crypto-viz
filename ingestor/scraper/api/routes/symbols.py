import mysql.connector
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..utils import JsonApiTemplate

router = APIRouter(
    prefix="/api",
    tags=["symbols"]
)

ApiResponse = JsonApiTemplate("api")

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
        cursor.execute("SELECT DISTINCT symbol FROM article ORDER BY symbol ASC")
        
        symbols = [row[0] for row in cursor.fetchall()]
        
        cursor.close()
        con.close()

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