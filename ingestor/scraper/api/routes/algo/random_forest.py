"""
API routes pour Random Forest - prédictions de tendance crypto
"""
from __future__ import annotations

import os
from typing import Literal

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse

from ingestor.scraper.api.utils.json_api_res_template import JsonApiTemplate
from ingestor.builder.algo import random_forest


router = APIRouter(prefix="/algo", tags=["algo", "ml"])
ApiResponse = JsonApiTemplate("api")


@router.post("/random-forest/train")
def train_random_forest(
    symbol: str | None = Query(None, description="Symbol to train on (None = all symbols)"),
    n_estimators: int = Query(100, ge=10, le=500, description="Number of trees in the forest"),
    max_depth: int | None = Query(10, ge=2, le=50, description="Max depth of trees"),
    test_size: float = Query(0.2, ge=0.1, le=0.5, description="Test split ratio"),
):
    """
    Entraîne un Random Forest Classifier sur les données SQLite.
    
    Features: price, volume_24h, market_cap, coin_circulating, moving averages
    Target: 1 si prix monte à la prochaine observation, 0 sinon
    
    Returns: métriques (accuracy, precision, recall, f1), feature importance, confusion matrix
    """
    try:
        result = random_forest.train_model(
            symbol=symbol,
            n_estimators=n_estimators,
            max_depth=max_depth,
            test_size=test_size
        )
        
        # Sauvegarder le modèle
        random_forest.save_model(result)
        
        response_data = {
            "symbol": result["symbol"],
            "metrics": result["metrics"],
            "feature_importance": result["feature_importance"],
            "model_params": {
                "n_estimators": n_estimators,
                "max_depth": max_depth,
                "test_size": test_size,
            }
        }
        
        return JSONResponse(
            content=ApiResponse._create_response(
                level="info",
                msg="Model trained and saved successfully",
                response=response_data
            ),
            status_code=200
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=ApiResponse._create_response(
                level="error",
                msg=str(e),
                response=[]
            )
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=ApiResponse._create_response(
                level="error",
                msg=f"Training failed: {str(e)}",
                response=[]
            )
        )


@router.get("/random-forest/predict")
def predict_random_forest(
    symbol: str = Query(..., description="Symbol to predict (e.g., BTC)"),
    recent_count: int = Query(1, ge=1, le=100, description="Number of recent observations to predict"),
):
    """
    Prédit la tendance (HAUSSE/BAISSE) pour les dernières observations d'un symbole.
    
    Returns: predictions avec probabilités et features utilisées
    """
    try:
        result = random_forest.predict(symbol=symbol, recent_count=recent_count)
        
        return JSONResponse(
            content=ApiResponse._create_response(
                level="info",
                msg="Predictions generated successfully",
                response=result
            ),
            status_code=200
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=ApiResponse._create_response(
                level="error",
                msg=str(e),
                response=[]
            )
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=ApiResponse._create_response(
                level="error",
                msg=f"Prediction failed: {str(e)}",
                response=[]
            )
        )


@router.get("/random-forest/info")
def model_info():
    """
    Retourne les informations sur le modèle entraîné (métriques, feature importance).
    """
    try:
        result = random_forest.load_model()
        
        response_data = {
            "symbol": result.get("symbol", "ALL"),
            "metrics": result.get("metrics", {}),
            "feature_importance": result.get("feature_importance", {}),
            "feature_names": result.get("feature_names", []),
        }
        
        return JSONResponse(
            content=ApiResponse._create_response(
                level="info",
                msg="Model info retrieved successfully",
                response=response_data
            ),
            status_code=200
        )
    
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=ApiResponse._create_response(
                level="error",
                msg="No trained model found. Train first via POST /algo/random-forest/train",
                response=[]
            )
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=ApiResponse._create_response(
                level="error",
                msg=f"Failed to load model info: {str(e)}",
                response=[]
            )
        )
