import fastapi
from fastapi import APIRouter

router = APIRouter(
    prefix="/health",
    tags=["health"]
)

@router.get("/check")
async def version():
    return {"version": fastapi.__version__}