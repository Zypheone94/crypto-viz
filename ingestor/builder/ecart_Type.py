import polars as pl
import sqlite3
from pathlib import Path


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
    
    # Filter out rows with null prices and ensure timestamp is datetime
    df_clean = (
        df.filter(pl.col("price_usd").is_not_null())
          .with_columns(pl.col("ts").cast(pl.Datetime(time_zone="UTC")))
          .sort(["symbol", "ts"])
    )
    
    # Calculate price changes and rolling standard deviation by symbol
    result = (
        df_clean
        .with_columns([
            # Calculate percentage change from previous price
            (pl.col("price_usd").pct_change().over("symbol") * 100).alias("price_change_pct"),
            
            # Calculate log returns for better statistical properties
            pl.col("price_usd").log().diff().over("symbol").alias("log_returns")
        ])
        .with_columns([
            # Rolling standard deviation of price changes (volatility)
            pl.col("price_change_pct")
              .rolling_std(window_size=period)
              .over("symbol")
              .alias("price_volatility_std"),
            
            # Rolling standard deviation of log returns  
            pl.col("log_returns")
              .rolling_std(window_size=period)
              .over("symbol")
              .alias("log_returns_std"),
              
            # Rolling mean for reference
            pl.col("price_change_pct")
              .rolling_mean(window_size=period)
              .over("symbol")
              .alias("price_change_mean"),
              
            # Z-score (how many standard deviations from mean)
            ((pl.col("price_change_pct") - pl.col("price_change_pct").rolling_mean(window_size=period).over("symbol"))
             / pl.col("price_change_pct").rolling_std(window_size=period).over("symbol"))
             .alias("price_change_zscore")
        ])
        .with_columns([
            # Volatility classification
            pl.when(pl.col("price_volatility_std") > pl.col("price_volatility_std").quantile(0.75).over("symbol"))
              .then(pl.lit("high"))
              .when(pl.col("price_volatility_std") > pl.col("price_volatility_std").quantile(0.25).over("symbol"))
              .then(pl.lit("medium"))
              .otherwise(pl.lit("low"))
              .alias("volatility_category"),
              
            # Flag for extreme movements (beyond 2 standard deviations)
            (pl.col("price_change_zscore").abs() > 2.0).alias("extreme_movement"),
            
            # Period used for calculation
            pl.lit(period).alias("ecart_type_period")
        ])
    )
    
    return result


def generate_sample_data() -> pl.DataFrame:
    """Generate sample cryptocurrency price data for testing"""
    import random
    from datetime import datetime, timedelta
    
    # Set seed for reproducible results
    random.seed(42)
    
    symbols = ["BTC", "ETH", "ADA", "DOT", "SOL"]
    base_prices = {"BTC": 45000, "ETH": 3000, "ADA": 0.5, "DOT": 25, "SOL": 100}
    
    data = []
    start_date = datetime(2024, 1, 1)
    
    for symbol in symbols:
        current_price = base_prices[symbol]
        current_date = start_date
        
        # Generate 100 data points per symbol
        for i in range(100):
            # Add some random volatility
            change_pct = random.gauss(0, 0.05)  # 5% standard deviation
            current_price = current_price * (1 + change_pct)
            
            data.append({
                "symbol": symbol,
                "price_usd": current_price,
                "ts": current_date
            })
            
            current_date += timedelta(hours=1)  # Hourly data
    
    return pl.DataFrame(data)


def test_ecart_type():
    """Test the écart type calculation with sample data"""
    print("=" * 50)
    print("Testing Écart Type Calculation")
    print("=" * 50)
    
    # Generate sample data
    print("1. Generating sample cryptocurrency data...")
    df = generate_sample_data()
    print(f"   Created {df.height} records for {df['symbol'].n_unique()} symbols")
    
    # Show sample of raw data
    print("\n2. Sample of raw data:")
    print(df.head().select(["symbol", "price_usd", "ts"]))
    
    # Calculate écart type
    print("\n3. Calculating écart type (standard deviation analysis)...")
    try:
        results = build_ecart_type(df, period=14)
        print("Analysis completed successfully!")
        print(f"Processed {results.height} records")
        
        # Show results summary
        print("\n4. Analysis Results Summary:")
        summary = (
            results
            .filter(pl.col("price_volatility_std").is_not_null())
            .group_by("symbol")
            .agg([
                pl.col("price_volatility_std").mean().alias("avg_volatility"),
                pl.col("price_volatility_std").max().alias("max_volatility"),
                pl.col("extreme_movement").sum().alias("extreme_movements"),
                pl.col("volatility_category").mode().first().alias("typical_category")
            ])
            .sort("avg_volatility", descending=True)
        )
        print(summary)
        
        # Show detailed results for one symbol
        print("\n5. Detailed results for BTC (last 10 records):")
        btc_details = (
            results
            .filter(pl.col("symbol") == "BTC")
            .filter(pl.col("price_volatility_std").is_not_null())
            .tail(10)
            .select([
                "ts", "price_usd", "price_change_pct", 
                "price_volatility_std", "volatility_category", 
                "extreme_movement", "price_change_zscore"
            ])
        )
        print(btc_details)
        
        # Statistical summary
        print("\n6. Overall Statistics:")
        stats = results.select([
            pl.col("price_volatility_std").mean().alias("mean_volatility"),
            pl.col("price_volatility_std").std().alias("volatility_of_volatility"),
            pl.col("extreme_movement").mean().alias("extreme_movement_rate"),
            pl.col("volatility_category").value_counts().alias("category_counts")
        ])
        
        print(f"   • Average volatility: {stats['mean_volatility'][0]:.4f}%")
        print(f"   • Volatility of volatility: {stats['volatility_of_volatility'][0]:.4f}%")
        print(f"   • Extreme movement rate: {stats['extreme_movement_rate'][0]:.2%}")
        
        print("Test completed successfully!")
        return results
        
    except Exception as e:
        print(f"Test failed: {e}")
        raise


def load_data_from_db(db_path: str | Path = None, limit: int = 1000) -> pl.DataFrame:
    """Load price data from the project's SQLite `article` table.

    Returns an empty DataFrame if the table doesn't exist or no rows are found.
    """
    if db_path is None:
        db_path = Path(__file__).parent.parent / "scraper/component/scraperdb/data/ingestor.db"
    db_path = Path(db_path)

    if not db_path.exists():
        raise FileNotFoundError(f"SQLite DB not found at {db_path}")

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
    ORDER BY symbol, date
    LIMIT ?
    '''

    try:
        with sqlite3.connect(str(db_path)) as con:
            df = pl.read_database(query, con, execute_options={"parameters": [limit]})

        if df.height == 0:
            return df

        # Ensure proper data types
        df = df.with_columns([
            pl.col("price_usd").cast(pl.Float64),
            pl.col("ts").cast(pl.Datetime(time_zone="UTC"))
        ])

        return df

    except sqlite3.OperationalError as e:
        raise sqlite3.OperationalError(f"Database error: {e}")


def calculate_ecart_type_analysis(period: int = 14, limit: int = 1000, db_path: str | Path = None) -> dict:
    """
    Calculate écart type analysis from database and return API-ready results.
    
    Returns:
        dict: Analysis results including summary statistics and detailed data
    """
    # Load data from database
    df = load_data_from_db(db_path, limit)
    
    if df.height == 0:
        return {
            "success": False,
            "message": "No data available",
            "data": None
        }
    
    # Calculate écart type
    results = build_ecart_type(df, period=period)
    
    # Generate summary statistics
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
    
    # Get latest values per symbol
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


def get_symbol_analysis(symbol: str, period: int = 14, limit: int = 1000, db_path: str | Path = None) -> dict:
    """
    Get écart type analysis for a specific symbol.
    
    Returns:
        dict: Analysis results for the specified symbol
    """
    # Load data from database
    df = load_data_from_db(db_path, limit)
    
    if df.height == 0:
        return {
            "success": False,
            "message": "No data available",
            "data": None
        }
    
    # Filter for specific symbol
    symbol_df = df.filter(pl.col("symbol") == symbol.upper())
    
    if symbol_df.height == 0:
        return {
            "success": False,
            "message": f"No data found for symbol {symbol}",
            "data": None
        }
    
    # Calculate écart type for this symbol
    results = build_ecart_type(symbol_df, period=period)
    
    if results.height == 0:
        return {
            "success": False,
            "message": f"No analysis results for symbol {symbol}",
            "data": None
        }
    
    # Get time series data
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
    
    # Get latest stats
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
