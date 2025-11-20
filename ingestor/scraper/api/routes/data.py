import sys
import sqlite3
from pathlib import Path as PathLib

from fastapi import APIRouter, Query, Path
from fastapi.responses import JSONResponse
from api.utils.json_api_res_template import JsonApiTemplate

# Add builder module to path for other imports if needed
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
            fetched_at as ts,
            name as title,
            url as source
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
            query += " AND DATE(fetched_at) >= ?"
            params.append(date_from)
        
        if date_to:
            query += " AND DATE(fetched_at) <= ?"
            params.append(date_to)
        
        query += " ORDER BY symbol, fetched_at LIMIT ?"
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
            pl.col("ts").str.to_datetime(format="%Y-%m-%dT%H:%M:%S.%f", time_zone="UTC")
        ])
        
        # Calculate écart type analysis
        from .algo.ecart_Type import build_ecart_type
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
            fetched_at as ts,
            name as title,
            url as source
        FROM article
        WHERE price IS NOT NULL
          AND symbol IS NOT NULL
          AND UPPER(symbol) = UPPER(?)
        '''
        params = [symbol]
        
        # Add date range filters
        if date_from:
            query += " AND DATE(fetched_at) >= ?"
            params.append(date_from)
        
        if date_to:
            query += " AND DATE(fetched_at) <= ?"
            params.append(date_to)
        
        query += " ORDER BY fetched_at LIMIT ?"
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
            pl.col("ts").str.to_datetime(format="%Y-%m-%dT%H:%M:%S.%f", time_zone="UTC")
        ])
        
        # Calculate écart type for this symbol
        from .algo.ecart_Type import build_ecart_type
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
        from .algo.ecart_Type import process_and_save_ecart_analysis
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


# RSI ROUTES

@router.get("/rsi")
async def get_rsi_analysis(
    period: int = Query(14, ge=5, le=100, description="Period for RSI calculation"),
    limit: int = Query(1000, ge=10, le=10000, description="Maximum number of records to analyze"),
    symbol: str = Query(None, description="Filter by specific cryptocurrency symbol (e.g., BTC, ETH)"),
    date_from: str = Query(None, description="Start date filter (YYYY-MM-DD format)"),
    date_to: str = Query(None, description="End date filter (YYYY-MM-DD format)")
):
    """
    Get RSI (Relative Strength Index) analysis for symbols in the database.
    
    RSI is a momentum oscillator that measures the speed and change of price movements.
    It oscillates between 0 and 100. Traditionally:
    - RSI > 70: Overbought condition (potential sell signal)
    - RSI < 30: Oversold condition (potential buy signal)
    - RSI around 50: Neutral momentum
    
    Returns:
    - Current RSI values and signals
    - Historical RSI trends
    - Overbought/oversold analysis
    - Momentum strength indicators
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
        
        # Load and filter data
        import polars as pl
        import sqlite3
        
        query_conditions = []
        query_params = []
        
        base_query = '''
        SELECT
            symbol,
            price as price_usd,
            fetched_at as ts,
            name as title,
            url as source
        FROM article
        WHERE price IS NOT NULL
          AND symbol IS NOT NULL
        '''
        
        if symbol:
            query_conditions.append("AND UPPER(symbol) = ?")
            query_params.append(symbol.upper())
        
        if date_from:
            query_conditions.append("AND DATE(fetched_at) >= ?")
            query_params.append(date_from)
        
        if date_to:
            query_conditions.append("AND DATE(fetched_at) <= ?")
            query_params.append(date_to)
        
        final_query = base_query + " " + " ".join(query_conditions) + " ORDER BY symbol, fetched_at LIMIT ?"
        query_params.append(limit)
        
        with sqlite3.connect(str(db_path)) as con:
            df = pl.read_database(final_query, con, execute_options={"parameters": query_params})
        
        if df.height == 0:
            response = ApiResponse._create_response(
                level="warning",
                msg="No data found matching the criteria",
                response=[]
            )
            return JSONResponse(content=response, status_code=200)
        
        # Process data
        df = df.with_columns([
            pl.col("price_usd").cast(pl.Float64),
            pl.col("ts").str.to_datetime(format="%Y-%m-%dT%H:%M:%S.%f", time_zone="UTC")
        ])
        
        # Import RSI module
        from rsi import build_rsi
        results_df = build_rsi(df, period=period)
        
        # Calculate summary statistics
        summary = (
            results_df
            .filter(pl.col("rsi").is_not_null())
            .group_by("symbol")
            .agg([
                pl.col("rsi").mean().alias("avg_rsi"),
                pl.col("rsi").max().alias("max_rsi"),
                pl.col("rsi").min().alias("min_rsi"),
                pl.col("rsi").std().alias("rsi_volatility"),
                (pl.col("rsi_signal") == "overbought").sum().alias("overbought_periods"),
                (pl.col("rsi_signal") == "oversold").sum().alias("oversold_periods"),
                pl.col("rsi_signal").mode().first().alias("dominant_signal"),
                pl.count().alias("data_points")
            ])
            .sort("avg_rsi", descending=True)
        )
        
        # Latest data
        latest_data = (
            results_df
            .filter(pl.col("rsi").is_not_null())
            .group_by("symbol")
            .agg([
                pl.col("ts").max().alias("latest_timestamp"),
                pl.col("price_usd").last().alias("latest_price"),
                pl.col("rsi").last().alias("current_rsi"),
                pl.col("rsi_signal").last().alias("current_signal"),
                pl.col("rsi_strength").last().alias("current_strength"),
                pl.col("rsi_momentum").last().alias("current_momentum")
            ])
        )
        
        def convert_datetime_to_string(obj):
            if isinstance(obj, list):
                return [convert_datetime_to_string(item) for item in obj]
            elif isinstance(obj, dict):
                return {key: convert_datetime_to_string(value) for key, value in obj.items()}
            elif hasattr(obj, 'isoformat'):
                return obj.isoformat()
            else:
                return obj
        
        api_data = {
            "metadata": {
                "period": period,
                "total_records": results_df.height,
                "symbols_analyzed": results_df["symbol"].n_unique(),
                "analysis_timestamp": results_df["ts"].max().isoformat() if results_df.height > 0 else None
            },
            "summary": convert_datetime_to_string(summary.to_dicts()),
            "latest_data": convert_datetime_to_string(latest_data.to_dicts())
        }
        
        response = ApiResponse._create_response(
            level="info",
            msg=f"RSI analysis completed for {results_df['symbol'].n_unique()} symbols",
            response=api_data
        )
        
        return JSONResponse(content=response, status_code=200)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        response = ApiResponse._create_response(
            level="error",
            msg=f"RSI analysis failed: {str(e)}",
            response={"error_details": error_details.split('\n')[-3:-1]}
        )
        return JSONResponse(content=response, status_code=500)


@router.get("/rsi/{symbol}")
async def get_symbol_rsi_analysis(
    symbol: str = Path(..., description="Cryptocurrency symbol (e.g., BTC, ETH)"),
    period: int = Query(14, ge=5, le=100, description="Period for RSI calculation"),
    limit: int = Query(1000, ge=10, le=10000, description="Maximum number of records to analyze"),
    date_from: str = Query(None, description="Start date filter (YYYY-MM-DD format)"),
    date_to: str = Query(None, description="End date filter (YYYY-MM-DD format)")
):
    """
    Get detailed RSI analysis for a specific cryptocurrency symbol.
    
    Returns comprehensive RSI data including:
    - Historical RSI values and trends
    - Current RSI signal (overbought/oversold/neutral)
    - RSI momentum changes
    - Trading strength indicators
    - Time series data for charting
    """
    try:
        # Use container database path
        db_path = PathLib("/app/ingestor/scraper/component/scraperdb/data/ingestor.db")
        
        if not db_path.exists():
            response = ApiResponse._create_response(
                level="error",
                msg=f"Database not found at {db_path}",
                response=[]
            )
            return JSONResponse(content=response, status_code=500)
        
        # Load and filter data for specific symbol
        import polars as pl
        import sqlite3
        
        query_conditions = ["AND UPPER(symbol) = ?"]
        query_params = [symbol.upper()]
        
        base_query = '''
        SELECT
            symbol,
            price as price_usd,
            fetched_at as ts,
            name as title,
            url as source
        FROM article
        WHERE price IS NOT NULL
          AND symbol IS NOT NULL
        '''
        
        if date_from:
            query_conditions.append("AND DATE(fetched_at) >= ?")
            query_params.append(date_from)
        
        if date_to:
            query_conditions.append("AND DATE(fetched_at) <= ?")
            query_params.append(date_to)
        
        final_query = base_query + " " + " ".join(query_conditions) + " ORDER BY fetched_at LIMIT ?"
        query_params.append(limit)
        
        with sqlite3.connect(str(db_path)) as con:
            df = pl.read_database(final_query, con, execute_options={"parameters": query_params})
        
        if df.height == 0:
            response = ApiResponse._create_response(
                level="warning",
                msg=f"No data found for symbol {symbol.upper()}",
                response={"symbol": symbol.upper()}
            )
            return JSONResponse(content=response, status_code=200)
        
        # Process data
        df = df.with_columns([
            pl.col("price_usd").cast(pl.Float64),
            pl.col("ts").str.to_datetime(format="%Y-%m-%dT%H:%M:%S.%f", time_zone="UTC")
        ])
        
        # Import and calculate RSI
        from rsi import build_rsi
        results_df = build_rsi(df, period=period)
        
        # Time series for charts
        time_series = (
            results_df
            .filter(pl.col("rsi").is_not_null())
            .select([
                "ts", "price_usd", "price_change_pct", 
                "rsi", "rsi_signal", "rsi_strength", 
                "rsi_momentum", "avg_gain", "avg_loss"
            ])
            .sort("ts")
        )
        
        # Latest statistics
        latest = results_df.tail(1).select([
            "price_usd", "rsi", "rsi_signal", "rsi_strength",
            "rsi_momentum", "avg_gain", "avg_loss"
        ]).to_dicts()[0] if results_df.height > 0 else {}
        
        def convert_datetime_to_string(obj):
            if isinstance(obj, list):
                return [convert_datetime_to_string(item) for item in obj]
            elif isinstance(obj, dict):
                return {key: convert_datetime_to_string(value) for key, value in obj.items()}
            elif hasattr(obj, 'isoformat'):
                return obj.isoformat()
            else:
                return obj
        
        api_data = {
            "symbol": symbol.upper(),
            "period": period,
            "latest_stats": convert_datetime_to_string(latest),
            "time_series": convert_datetime_to_string(time_series.to_dicts()),
            "metadata": {
                "total_points": results_df.height,
                "date_range": {
                    "start": results_df["ts"].min().isoformat() if results_df.height > 0 else None,
                    "end": results_df["ts"].max().isoformat() if results_df.height > 0 else None
                }
            }
        }
        
        response = ApiResponse._create_response(
            level="info",
            msg=f"RSI analysis completed for {symbol.upper()}",
            response=api_data
        )
        
        return JSONResponse(content=response, status_code=200)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        response = ApiResponse._create_response(
            level="error",
            msg=f"RSI analysis failed for {symbol}: {str(e)}",
            response={"error_details": error_details.split('\n')[-3:-1]}
        )
        return JSONResponse(content=response, status_code=500)


@router.post("/rsi/calculate")
async def trigger_rsi_calculation(
    period: int = Query(14, ge=5, le=100, description="Period for RSI calculation"),
    limit: int = Query(1000, ge=10, le=10000, description="Maximum number of records to process")
):
    """
    Trigger RSI calculation for all symbols and save results to database.
    
    This endpoint processes all available price data and calculates RSI indicators,
    storing the results for faster subsequent queries.
    """
    try:
        # Use container database path
        db_path = PathLib("/app/ingestor/scraper/component/scraperdb/data/ingestor.db")
        
        from rsi import process_and_save_rsi_analysis
        results = process_and_save_rsi_analysis(period=period, limit=limit, db_path=str(db_path))
        
        if not results['success']:
            response = ApiResponse._create_response(
                level="error",
                msg=results['message'],
                response=results
            )
            return JSONResponse(content=response, status_code=500)
        
        def convert_datetime_to_string(obj):
            if isinstance(obj, list):
                return [convert_datetime_to_string(item) for item in obj]
            elif isinstance(obj, dict):
                return {key: convert_datetime_to_string(value) for key, value in obj.items()}
            elif hasattr(obj, 'isoformat'):
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
            msg="RSI calculation triggered successfully",
            response=api_data
        )
        
        return JSONResponse(content=response, status_code=200)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        response = ApiResponse._create_response(
            level="error",
            msg=f"RSI calculation failed: {str(e)}",
            response={"error_details": error_details.split('\n')[-3:-1]}
        )
        return JSONResponse(content=response, status_code=500)


@router.get("/news")
async def get_news_articles(
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of news articles to return")
):
    """
    Get crypto news articles from the data/news.json file.
    
    Returns news articles transformed to match the frontend interface expectations.
    """
    try:
        import json
        
        # Path to news.json file (in the root data folder)
        news_file_path = PathLib(__file__).parent.parent.parent.parent.parent / "data" / "news.json"
        
        if not news_file_path.exists():
            response = ApiResponse._create_response(
                level="error",
                msg="News data file not found",
                response={"articles": []}
            )
            return JSONResponse(content=response, status_code=404)
        
        articles = []
        
        # Read JSONL format (each line is a JSON object)
        with open(news_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()[:limit]  # Apply limit early for performance
            
        for line in lines:
            try:
                news_item = json.loads(line.strip())
                
                # Transform the data structure to match frontend interface
                transformed_article = {
                    "title": news_item.get("title", ""),
                    "link": news_item.get("url", ""),
                    "section": news_item.get("source", "crypto").lower(),
                    "timestamp": news_item.get("published_at", ""),
                    "scraped_at": news_item.get("fetched_at", ""),
                    "content": news_item.get("content", ""),
                    "has_content": bool(news_item.get("content", "").strip())
                }
                
                # Only include articles with content
                if transformed_article["has_content"]:
                    articles.append(transformed_article)
                    
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON line: {e}")
                continue
        
        response = ApiResponse._create_response(
            level="success",
            msg=f"Retrieved {len(articles)} news articles successfully",  
            response={"articles": articles}
        )
        return JSONResponse(content=response, status_code=200)
        
    except Exception as e:
        print(f"Error reading news data: {e}")
        error_details = f"Exception: {type(e).__name__}: {str(e)}"
        response = ApiResponse._create_response(
            level="error",
            msg=f"Failed to retrieve news articles: {str(e)}",
            response={"error_details": error_details.split('\n')[-3:-1]}
        )
        return JSONResponse(content=response, status_code=500)
