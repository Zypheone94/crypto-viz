

from fastapi import APIRouter
from ingestor.scraper.api.utils.json_api_res_template import JsonApiTemplate
from ingestor.scraper.component.scraperdb.mlpredictor import predict_symbol_window

router = APIRouter(
    prefix="/ml",
    tags=["ml"],
)

ApiResponse = JsonApiTemplate("api")


@router.get("/api/predict")
async def predict_endpoint(symbol: str, date_start: str | None = None):
    result = predict_symbol_window(symbol, date_start)

    if not result["success"]:
        return ApiResponse._create_response(
            level="error",
            msg=result["message"],
            response={"status": 400, "data": None},
        )

    return ApiResponse._create_response(
        level="info",
        msg=result["message"],
        response={"status": 200, "data": result["data"]},
    )
