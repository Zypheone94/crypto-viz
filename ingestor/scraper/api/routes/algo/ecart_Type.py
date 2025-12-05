import polars as pl
import sqlite3
import sys
from pathlib import Path

# Import MySQL client utilities
sys.path.append(str(Path(__file__).parent.parent / "utils"))
from mysql_client import load_symbol_data


def build_ecart_type(df: pl.DataFrame, period: int = 14) -> pl.DataFrame:
    """
    Calculate the standard deviation (écart type) of price movements over a rolling window.
    
    Args:
        df: DataFrame with columns 'symbol', 'price_usd', and 'ts' (timestamp)
        period: Rolling window size in periods (default: 14)
        
    Returns:
        DataFrame with additional columns for standard deviation calculations
    """
    # Ensure we have the required columns
    required_cols = {"symbol", "price_usd", "ts"}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    # Handle both string and datetime inputs for ts column
    ts_col = pl.col("ts")
    if df.dtypes[df.columns.index("ts")] == pl.String:
        ts_col = ts_col.str.to_datetime(format="%Y-%m-%d %H:%M:%S", time_zone="UTC")
    elif df.dtypes[df.columns.index("ts")] != pl.Datetime:
        ts_col = ts_col.cast(pl.Datetime(time_zone="UTC"))
    
    df_clean = (
        df.filter(pl.col("price_usd").is_not_null())
          .with_columns(ts_col.alias("ts"))
          .sort(["symbol", "ts"])
    )
    
    # Check if we have a single symbol (common case for symbol-specific queries)
    unique_symbols = df_clean["symbol"].n_unique() if "symbol" in df_clean.columns else 1
    is_single_symbol = unique_symbols == 1
    
    # Calculate price changes and log returns
    # Use .over("symbol") only if multiple symbols, otherwise calculate directly
    if is_single_symbol:
        df_with_changes = df_clean.with_columns([
            (pl.col("price_usd").pct_change() * 100).alias("price_change_pct"),
            pl.col("price_usd").log().diff().alias("log_returns")
        ])
        
        # Calculate rolling statistics without grouping for single symbol
        rolling_std = pl.col("price_change_pct").rolling_std(window_size=period)
        rolling_mean = pl.col("price_change_pct").rolling_mean(window_size=period)
        
        df_with_rolling = df_with_changes.with_columns([
            rolling_std.alias("price_volatility_std"),
            pl.col("log_returns").rolling_std(window_size=period).alias("log_returns_std"),
            rolling_mean.alias("price_change_mean"),
            # Z-score calculation with division by zero protection
            pl.when(rolling_std > 0)
              .then((pl.col("price_change_pct") - rolling_mean) / rolling_std)
              .otherwise(pl.lit(None))
              .alias("price_change_zscore")
        ])
    else:
        # Multiple symbols - use grouping
        df_with_changes = df_clean.with_columns([
            (pl.col("price_usd").pct_change().over("symbol") * 100).alias("price_change_pct"),
            pl.col("price_usd").log().diff().over("symbol").alias("log_returns")
        ])
        
        rolling_std = pl.col("price_change_pct").rolling_std(window_size=period).over("symbol")
        rolling_mean = pl.col("price_change_pct").rolling_mean(window_size=period).over("symbol")
        
        df_with_rolling = df_with_changes.with_columns([
            rolling_std.alias("price_volatility_std"),
            pl.col("log_returns").rolling_std(window_size=period).over("symbol").alias("log_returns_std"),
            rolling_mean.alias("price_change_mean"),
            # Z-score calculation with division by zero protection
            pl.when(rolling_std > 0)
              .then((pl.col("price_change_pct") - rolling_mean) / rolling_std)
              .otherwise(pl.lit(None))
              .alias("price_change_zscore")
        ])
    
    # Calculate volatility category - handle cases with insufficient data for quantiles
    # For single symbol, calculate quantiles without grouping
    try:
        if is_single_symbol:
            # Single symbol: calculate quantiles directly without grouping
            volatility_values = df_with_rolling.filter(pl.col("price_volatility_std").is_not_null())["price_volatility_std"]
            if volatility_values.len() > 0:
                q75 = volatility_values.quantile(0.75)
                q25 = volatility_values.quantile(0.25)
                result = df_with_rolling.with_columns([
                    pl.when(pl.col("price_volatility_std").is_not_null())
                      .then(
                          pl.when(pl.col("price_volatility_std") > q75)
                            .then(pl.lit("high"))
                            .when(pl.col("price_volatility_std") > q25)
                            .then(pl.lit("medium"))
                            .otherwise(pl.lit("low"))
                      )
                      .otherwise(pl.lit(None))
                      .alias("volatility_category"),
                    pl.when(pl.col("price_change_zscore").is_not_null())
                      .then(pl.col("price_change_zscore").abs() > 2.0)
                      .otherwise(pl.lit(False))
                      .alias("extreme_movement"),
                    pl.lit(period).alias("ecart_type_period")
                ])
            else:
                # No valid volatility data, use default
                result = df_with_rolling.with_columns([
                    pl.lit(None).alias("volatility_category"),
                    pl.lit(False).alias("extreme_movement"),
                    pl.lit(period).alias("ecart_type_period")
                ])
        else:
            # Multiple symbols: use grouping
            result = df_with_rolling.with_columns([
                pl.when(pl.col("price_volatility_std").is_not_null())
                  .then(
                      pl.when(pl.col("price_volatility_std") > pl.col("price_volatility_std").quantile(0.75).over("symbol"))
                        .then(pl.lit("high"))
                        .when(pl.col("price_volatility_std") > pl.col("price_volatility_std").quantile(0.25).over("symbol"))
                        .then(pl.lit("medium"))
                        .otherwise(pl.lit("low"))
                  )
                  .otherwise(pl.lit(None))
                  .alias("volatility_category"),
                pl.when(pl.col("price_change_zscore").is_not_null())
                  .then(pl.col("price_change_zscore").abs() > 2.0)
                  .otherwise(pl.lit(False))
                  .alias("extreme_movement"),
                pl.lit(period).alias("ecart_type_period")
            ])
    except Exception:
        # Fallback if quantile calculation fails (insufficient data)
        result = df_with_rolling.with_columns([
            pl.when(pl.col("price_volatility_std").is_not_null())
              .then(pl.lit("medium"))  # Default category
              .otherwise(pl.lit(None))
              .alias("volatility_category"),
            pl.when(pl.col("price_change_zscore").is_not_null())
              .then(pl.col("price_change_zscore").abs() > 2.0)
              .otherwise(pl.lit(False))
              .alias("extreme_movement"),
            pl.lit(period).alias("ecart_type_period")
        ])
    
    return result


def load_data_from_db(db_path: str | Path = None, limit: int = 1000) -> pl.DataFrame:
    """
    Load cryptocurrency data from MySQL database for écart-type analysis.
    Note: db_path parameter is kept for compatibility but not used with MySQL.
    """
    try:
        # Use the MySQL client to load data
        df = load_symbol_data(symbol=None, limit=limit)
        return df
    except Exception as e:
        raise Exception(f"MySQL database error: {e}")
def calculate_ecart_type_analysis(period: int = 14, limit: int = 1000, db_path: str | Path = None) -> dict:
    df = load_data_from_db(db_path, limit)
    
    if df.height == 0:
        return {
            "success": False,
            "message": "No data available",
            "data": None
        }
    
    results = build_ecart_type(df, period=period)
    summary = (
        results
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
    
    latest_data = (
        results
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
    
    return {
        "success": True,
        "message": "Analysis completed successfully",
        "metadata": {
            "period": period,
            "total_records": results.height,
            "symbols_analyzed": results["symbol"].n_unique(),
            "analysis_timestamp": results["ts"].max() if results.height > 0 else None
        },
        "summary": summary.to_dicts(),
        "latest_data": latest_data.to_dicts(),
        "detailed_results": results.to_dicts() if results.height <= 1000 else None  # Limit detailed data for API
    }


def get_symbol_analysis(symbol: str, period: int = 14, limit: int = 1000) -> dict:
    """
    Get écart-type analysis for a specific symbol using MySQL.
    """
    try:
        # Load data directly for the specific symbol using MySQL client
        df = load_symbol_data(symbol=symbol, limit=limit)

        if df.height == 0:
            return {
                "success": False,
                "message": f"No data found for symbol {symbol}",
                "data": None
            }
        
        # Calculate écart-type analysis
        results = build_ecart_type(df, period=period)
    except Exception as e:
        return {
            "success": False,
            "message": f"Database error: {str(e)}",
            "data": None
        }
    
    if results.height == 0:
        return {
            "success": False,
            "message": f"No analysis results for symbol {symbol}",
            "data": None
        }
    
    time_series = (
        results
        .filter(pl.col("price_volatility_std").is_not_null())
        .select([
            "ts", "price_usd", "price_change_pct", 
            "price_volatility_std", "volatility_category", 
            "extreme_movement", "price_change_zscore"
        ])
        .sort("ts")
    )
    
    latest = results.tail(1).select([
        "price_usd", "price_volatility_std", "volatility_category",
        "extreme_movement", "price_change_zscore"
    ]).to_dicts()[0] if results.height > 0 else {}
    
    return {
        "success": True,
        "symbol": symbol.upper(),
        "period": period,
        "latest_stats": latest,
        "time_series": time_series.to_dicts(),
        "metadata": {
            "total_points": results.height,
            "date_range": {
                "start": results["ts"].min(),
                "end": results["ts"].max()
            }
        }
    }



def load_saved_ecart_analysis(db_path: str | Path = None, limit: int = 1000) -> pl.DataFrame:
    if db_path is None:
        db_path = Path(__file__).parent.parent / "scraper/component/scraperdb/data/ingestor.db"
    db_path = Path(db_path)
    
    if not db_path.exists():
        raise FileNotFoundError(f"SQLite DB not found at {db_path}")
    
    query = '''
    SELECT 
        symbol, timestamp as ts, price_usd, price_change_pct, log_returns,
        price_volatility_std, log_returns_std, price_change_mean,
        price_change_zscore, volatility_category, extreme_movement,
        ecart_type_period, created_at
    FROM ecart_type_analysis
    ORDER BY symbol, timestamp
    LIMIT ?
    '''
    
    try:
        with sqlite3.connect(str(db_path)) as con:
            df = pl.read_database(query, con, execute_options={"parameters": [limit]})
        
        if df.height > 0:
            df = df.with_columns([
                pl.col("ts").str.to_datetime(time_zone="UTC"),  # ISO format auto-detection
                pl.col("price_usd").cast(pl.Float64),
                pl.col("price_change_pct").cast(pl.Float64),
                pl.col("price_volatility_std").cast(pl.Float64),
                pl.col("extreme_movement").cast(pl.Boolean)
            ])
        
        return df
        
    except sqlite3.OperationalError as e:
        raise sqlite3.OperationalError(f"Database error: {e}")


def save_ecart_analysis_to_db(results_df: pl.DataFrame, db_path: str | Path = None) -> bool:
    if db_path is None:
        db_path = Path(__file__).parent.parent / "scraper/component/scraperdb/data/ingestor.db"
    db_path = Path(db_path)
    
    try:
        with sqlite3.connect(str(db_path)) as con:
            con.execute("DELETE FROM ecart_type_analysis")
            
            for row in results_df.to_dicts():
                con.execute("""
                    INSERT INTO ecart_type_analysis (
                        symbol, timestamp, price_usd, price_change_pct, log_returns,
                        price_volatility_std, log_returns_std, price_change_mean,
                        price_change_zscore, volatility_category, extreme_movement,
                        ecart_type_period, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """, (
                    row.get('symbol'),
                    row.get('ts'),
                    row.get('price_usd'),
                    row.get('price_change_pct'),
                    row.get('log_returns'),
                    row.get('price_volatility_std'),
                    row.get('log_returns_std'),
                    row.get('price_change_mean'),
                    row.get('price_change_zscore'),
                    row.get('volatility_category'),
                    row.get('extreme_movement'),
                    row.get('ecart_type_period')
                ))
            
            con.commit()
            print(f"Successfully saved {results_df.height} ecart type analysis records to database")
            return True
            
    except Exception as e:
        print(f"Error saving ecart analysis to database: {e}")
        return False


def process_and_save_ecart_analysis(period: int = 14, limit: int = 1000, db_path: str | Path = None) -> dict:
    try:
        df = load_data_from_db(db_path, limit)
        
        if df.height == 0:
            return {
                "success": False,
                "message": "No data available for analysis",
                "data": None
            }
        
        results_df = build_ecart_type(df, period=period)
        
        if results_df.height == 0:
            return {
                "success": False,
                "message": "No analysis results generated",
                "data": None
            }
        
        saved = save_ecart_analysis_to_db(results_df, db_path)
        
        if not saved:
            print("Warning: Failed to save results to database, but analysis completed")
        
        analysis_results = calculate_ecart_type_analysis(period=period, limit=limit, db_path=db_path)
        
        print("Ecart type analysis completed successfully")
        print(f"Analyzed {results_df['symbol'].n_unique()} symbols")
        print(f"Total records: {results_df.height}")
        print(f"Results saved to database: {saved}")
        
        return analysis_results
        
    except Exception as e:
        print(f"Error processing ecart analysis: {e}")
        return {
            "success": False,
            "message": f"Analysis failed: {str(e)}",
            "data": None
        }


if __name__ == "__main__":
    analysis_results = process_and_save_ecart_analysis()
    print(f"Analysis completed: {analysis_results['success']}")
    if analysis_results['success']:
        print(f"Message: {analysis_results['message']}")
        if 'summary' in analysis_results:
            print(f"Symbols analyzed: {len(analysis_results['summary'])}")
