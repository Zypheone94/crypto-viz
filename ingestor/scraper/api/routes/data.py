import sys
import sqlite3
from pathlib import Path as PathLib

from fastapi import APIRouter, Query, Path
from fastapi.responses import JSONResponse
from api.utils.json_api_res_template import JsonApiTemplate

# Add builder module to path for ecart_Type imports
builder_path = PathLib(__file__).parent.parent.parent.parent / "builder"
sys.path.append(str(builder_path))

router = APIRouter(prefix="/data", tags=["data"])
ApiResponse = JsonApiTemplate("api")


@router.get("/ecart-type")
async def get_ecart_type_analysis(
    period: int = Query(14, ge=5, le=100, description="Rolling window period for volatility calculation"),
    limit: int = Query(1000, ge=10, le=10000, description="Maximum number of records to analyze"),
    symbol: str = Query(None, description="Filter by specific cryptocurrency symbol (e.g., BTC, ETH)"),
    date_from: str = Query(None, description="Start date filter (YYYY-MM-DD format)"),
    date_to: str = Query(None, description="End date filter (YYYY-MM-DD format)")
):
    """
    Get écart type (standard deviation) analysis for symbols in the database.
    
    This endpoint calculates volatility metrics including:
    - Rolling standard deviation of price changes
    - Volatility categories (low, medium, high)
    - Extreme movement detection
    - Z-score analysis
    
    Filters:
    - symbol: Filter by specific cryptocurrency (optional)
    - date_from/date_to: Filter by date range (optional)
    """
    try:
        # Use container database path
        db_path = PathLib("/app/ingestor/scraper/component/scraperdb/data/ingestor.db")
        
        # Check if database exists
        if not db_path.exists():
            response = ApiResponse._create_response(
                level="error",
                msg=f"Database not found at {db_path}",
                response=[]
            )
            return JSONResponse(content=response, status_code=500)
        
        # Load data with filters
        import polars as pl
        
        # Build query with filters
        query = '''
        SELECT
            symbol,
            price as price_usd,
            date as ts,
            titre as title,
            source
        FROM article
        WHERE price IS NOT NULL
          AND symbol IS NOT NULL
        '''
        params = []
        
        # Add symbol filter
        if symbol:
            query += " AND UPPER(symbol) = UPPER(?)"
            params.append(symbol)
        
        # Add date range filters
        if date_from:
            query += " AND date >= ?"
            params.append(date_from)
        
        if date_to:
            query += " AND date <= ?"
            params.append(date_to)
        
        query += " ORDER BY symbol, date LIMIT ?"
        params.append(limit)
        
        # Load filtered data
        with sqlite3.connect(str(db_path)) as con:
            df = pl.read_database(query, con, execute_options={"parameters": params})
        
        if df.height == 0:
            response = ApiResponse._create_response(
                level="warning",
                msg="No data found matching the specified filters",
                response=[]
            )
            return JSONResponse(content=response, status_code=200)
        
        # Ensure proper data types
        df = df.with_columns([
            pl.col("price_usd").cast(pl.Float64),
            pl.col("ts").str.to_datetime(format="%Y-%m-%d %H:%M:%S", time_zone="UTC")
        ])
        
        # Calculate écart type analysis
        from ecart_Type import build_ecart_type
        results_df = build_ecart_type(df, period=period)
        
        # Generate summary statistics
        summary = (
            results_df
            .filter(pl.col("price_volatility_std").is_not_null())
            .group_by("symbol")
            .agg([
                pl.col("price_volatility_std").mean().alias("avg_volatility"),
                pl.col("price_volatility_std").max().alias("max_volatility"),
                pl.col("price_volatility_std").min().alias("min_volatility"),
                pl.col("extreme_movement").sum().alias("extreme_movements"),
                pl.col("volatility_category").mode().first().alias("typical_category"),
                pl.count().alias("data_points")
            ])
            .sort("avg_volatility", descending=True)
        )
        
        # Get latest values per symbol
        latest_data = (
            results_df
            .filter(pl.col("price_volatility_std").is_not_null())
            .group_by("symbol")
            .agg([
                pl.col("ts").max().alias("latest_timestamp"),
                pl.col("price_usd").last().alias("latest_price"),
                pl.col("price_volatility_std").last().alias("current_volatility"),
                pl.col("volatility_category").last().alias("current_category"),
                pl.col("extreme_movement").last().alias("is_extreme_movement"),
                pl.col("price_change_zscore").last().alias("current_zscore")
            ])
        )
        
        results = {
            "success": True,
            "message": "Analysis completed successfully",
            "metadata": {
                "period": period,
                "total_records": results_df.height,
                "symbols_analyzed": results_df["symbol"].n_unique(),
                "analysis_timestamp": results_df["ts"].max() if results_df.height > 0 else None,
                "filters": {
                    "symbol": symbol,
                    "date_from": date_from,
                    "date_to": date_to
                }
            },
            "summary": summary.to_dicts(),
            "latest_data": latest_data.to_dicts(),
            "detailed_results": results_df.to_dicts() if results_df.height <= 500 else None
        }
        
        if not results['success']:
            level = "warning" if "No data" in results['message'] else "error"
            response = ApiResponse._create_response(
                level=level, 
                msg=results['message'], 
                response=[]
            )
            return JSONResponse(content=response, status_code=200 if level == "warning" else 500)
        
        # Format response for API - convert datetime objects to strings
        from datetime import datetime
        
        def convert_datetime_to_string(obj):
            """Convert datetime objects to ISO format strings"""
            if isinstance(obj, dict):
                return {key: convert_datetime_to_string(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_datetime_to_string(item) for item in obj]
            elif isinstance(obj, datetime):
                return obj.isoformat()
            else:
                return obj
        
        api_data = {
            "metadata": convert_datetime_to_string(results['metadata']),
            "summary": convert_datetime_to_string(results['summary']),
            "latest_data": convert_datetime_to_string(results['latest_data'])
        }
        
        # Include detailed results if available and not too large
        if results.get('detailed_results') and len(results['detailed_results']) <= 500:
            api_data['detailed_results'] = convert_datetime_to_string(results['detailed_results'])
        
        response = ApiResponse._create_response(
            level="info",
            msg="Écart type analysis completed successfully",
            response=api_data
        )
        
        return JSONResponse(content=response, status_code=200)
        
    except Exception as e:
        # Get more detailed error information
        import traceback
        error_details = traceback.format_exc()
        
        response = ApiResponse._create_response(
            level="error",
            msg=f"Écart type analysis failed: {str(e)}",
            response={"error_details": error_details.split('\n')[-3:-1]}  # Last 2 lines of traceback
        )
        return JSONResponse(content=response, status_code=500)


@router.get("/ecart-type/{symbol}")
async def get_symbol_ecart_type_analysis(
    symbol: str = Path(..., description="Cryptocurrency symbol (e.g., BTC, ETH)"),
    period: int = Query(14, ge=5, le=100, description="Rolling window period for volatility calculation"),
    limit: int = Query(1000, ge=10, le=10000, description="Maximum number of records to analyze"),
    date_from: str = Query(None, description="Start date filter (YYYY-MM-DD format)"),
    date_to: str = Query(None, description="End date filter (YYYY-MM-DD format)")
):
    """
    Get écart type analysis for a specific cryptocurrency symbol.
    
    Returns detailed time series data and statistics for the specified symbol.
    Supports date range filtering.
    """
    try:
        # Use container database path
        db_path = PathLib("/app/ingestor/scraper/component/scraperdb/data/ingestor.db")
        
        # Load data with symbol and date filters
        import polars as pl
        
        query = '''
        SELECT
            symbol,
            price as price_usd,
            date as ts,
            titre as title,
            source
        FROM article
        WHERE price IS NOT NULL
          AND symbol IS NOT NULL
          AND UPPER(symbol) = UPPER(?)
        '''
        params = [symbol]
        
        # Add date range filters
        if date_from:
            query += " AND date >= ?"
            params.append(date_from)
        
        if date_to:
            query += " AND date <= ?"
            params.append(date_to)
        
        query += " ORDER BY date LIMIT ?"
        params.append(limit)
        
        # Load filtered data
        with sqlite3.connect(str(db_path)) as con:
            df = pl.read_database(query, con, execute_options={"parameters": params})
        
        if df.height == 0:
            response = ApiResponse._create_response(
                level="warning",
                msg=f"No data found for symbol {symbol} in the specified date range",
                response=[]
            )
            return JSONResponse(content=response, status_code=404)
        
        # Ensure proper data types
        df = df.with_columns([
            pl.col("price_usd").cast(pl.Float64),
            pl.col("ts").str.to_datetime(format="%Y-%m-%d %H:%M:%S", time_zone="UTC")
        ])
        
        # Calculate écart type for this symbol
        from ecart_Type import build_ecart_type
        results_df = build_ecart_type(df, period=period)
        
        if results_df.height == 0:
            response = ApiResponse._create_response(
                level="warning",
                msg=f"No analysis results for symbol {symbol}",
                response=[]
            )
            return JSONResponse(content=response, status_code=404)
        
        # Get time series data
        time_series = (
            results_df
            .filter(pl.col("price_volatility_std").is_not_null())
            .select([
                "ts", "price_usd", "price_change_pct", 
                "price_volatility_std", "volatility_category", 
                "extreme_movement", "price_change_zscore"
            ])
            .sort("ts")
        )
        
        # Get latest stats
        latest = results_df.tail(1).select([
            "price_usd", "price_volatility_std", "volatility_category",
            "extreme_movement", "price_change_zscore"
        ]).to_dicts()[0] if results_df.height > 0 else {}
        
        # Convert datetime objects to strings
        from datetime import datetime
        
        def convert_datetime_to_string(obj):
            if isinstance(obj, dict):
                return {key: convert_datetime_to_string(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_datetime_to_string(item) for item in obj]
            elif isinstance(obj, datetime):
                return obj.isoformat()
            else:
                return obj
        
        results = {
            "success": True,
            "symbol": symbol.upper(),
            "period": period,
            "latest_stats": convert_datetime_to_string(latest),
            "time_series": convert_datetime_to_string(time_series.to_dicts()),
            "metadata": {
                "total_points": results_df.height,
                "date_range": {
                    "start": results_df["ts"].min().isoformat() if results_df.height > 0 else None,
                    "end": results_df["ts"].max().isoformat() if results_df.height > 0 else None
                },
                "filters": {
                    "date_from": date_from,
                    "date_to": date_to
                }
            }
        }
        
        response = ApiResponse._create_response(
            level="info",
            msg=f"Écart type analysis for {symbol} completed successfully",
            response=results
        )
        
        return JSONResponse(content=response, status_code=200)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        response = ApiResponse._create_response(
            level="error",
            msg=f"Analysis failed for {symbol}: {str(e)}",
            response={"error_details": error_details.split('\n')[-3:-1]}
        )
        return JSONResponse(content=response, status_code=500)


@router.post("/ecart-type/calculate")
async def trigger_ecart_type_calculation(
    period: int = Query(14, ge=5, le=100, description="Rolling window period for volatility calculation"),
    limit: int = Query(1000, ge=10, le=10000, description="Maximum number of records to analyze")
):
    """
    Trigger a new écart type calculation and save results.
    
    This endpoint processes the latest data from the database and calculates
    fresh volatility metrics for all available symbols.
    """
    try:
        from ecart_Type import process_and_save_ecart_analysis
        results = process_and_save_ecart_analysis(period=period, limit=limit)
        
        if not results['success']:
            level = "warning" if "No data" in results['message'] else "error"
            response = ApiResponse._create_response(
                level=level,
                msg=results['message'],
                response=[]
            )
            return JSONResponse(content=response, status_code=200 if level == "warning" else 500)
        
        # Convert datetime objects to strings
        from datetime import datetime
        
        def convert_datetime_to_string(obj):
            if isinstance(obj, dict):
                return {key: convert_datetime_to_string(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_datetime_to_string(item) for item in obj]
            elif isinstance(obj, datetime):
                return obj.isoformat()
            else:
                return obj
        
        # Return summary data only for POST response
        api_data = {
            "metadata": convert_datetime_to_string(results['metadata']),
            "summary": convert_datetime_to_string(results['summary'][:10])  # Limit to top 10
        }
        
        response = ApiResponse._create_response(
            level="info",
            msg="Écart type calculation triggered successfully",
            response=api_data
        )
        
        return JSONResponse(content=response, status_code=200)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        response = ApiResponse._create_response(
            level="error",
            msg=f"Calculation failed: {str(e)}",
            response={"error_details": error_details.split('\n')[-3:-1]}
        )
        return JSONResponse(content=response, status_code=500)
