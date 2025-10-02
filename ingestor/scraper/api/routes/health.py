import fastapi
from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter(
    prefix="/api/health",
    tags=["health"]
)

startup_time = datetime.now(timezone.utc)

@router.get("/check")
async def version():
    now = datetime.now(timezone.utc)
    delta = now - startup_time

    return {
        "status": 200,
        "version": fastapi.__version__,
        "upTime": str(delta.total_seconds())
    }