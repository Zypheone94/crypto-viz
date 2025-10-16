import fastapi
from fastapi import APIRouter
from datetime import datetime, timezone
from ..utils import JsonApiTemplate

router = APIRouter(
    prefix="/api/health",
    tags=["health"]
)

ApiResponse = JsonApiTemplate("api")

startup_time = datetime.now(timezone.utc)

@router.get("/check")
async def version():
    now = datetime.now(timezone.utc)
    delta = now - startup_time

    myResponse = ApiResponse._create_response(
        level="info",
        msg="Health Status",
        response={
        "status": 200,
        "version": fastapi.__version__,
        "upTime": str(delta.total_seconds())
        }
    )

    return myResponse