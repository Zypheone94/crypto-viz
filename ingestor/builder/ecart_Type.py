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
            pl.col("ts").str.to_datetime(format="%Y-%m-%d %H:%M:%S", time_zone="UTC")
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


def create_sample_data_in_db(db_path: str | Path = None) -> bool:
    """
    Create sample data in the database for testing the ecart type analysis.
    
    Returns:
        bool: True if successful, False otherwise
    """
    if db_path is None:
        db_path = Path(__file__).parent.parent / "scraper/component/scraperdb/data/ingestor.db"
    db_path = Path(db_path)
    
    try:
        # Generate sample data
        df = generate_sample_data()
        
        # Connect to database and insert data
        with sqlite3.connect(str(db_path)) as con:
            # First, ensure symbols exist in symbol table
            symbols = df['symbol'].unique().to_list()
            for symbol in symbols:
                con.execute("INSERT OR IGNORE INTO symbol (symbol) VALUES (?)", (symbol,))
            
            # Insert sample data into article table
            for row in df.to_dicts():
                con.execute("""
                    INSERT INTO article (date, titre, url, source, symbol, name, price, market_cap, coin_circulating)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row['ts'],
                    f"Sample article for {row['symbol']}",
                    "https://example.com",
                    "sample_source",
                    row['symbol'],
                    row['symbol'],  # Using symbol as name for now
                    row['price_usd'],
                    row['price_usd'] * 1000000,  # Mock market cap
                    1000000.0  # Mock circulating supply
                ))
            
            con.commit()
            print(f"Successfully inserted {df.height} sample records into database")
            return True
            
    except Exception as e:
        print(f"Error creating sample data: {e}")
        return False


def load_saved_ecart_analysis(db_path: str | Path = None, limit: int = 1000) -> pl.DataFrame:
    """
    Load previously saved ecart type analysis results from the database.
    
    Returns:
        pl.DataFrame: Saved analysis results
    """
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
            # Ensure proper data types
            df = df.with_columns([
                pl.col("ts").str.to_datetime(format="%Y-%m-%d %H:%M:%S", time_zone="UTC"),
                pl.col("price_usd").cast(pl.Float64),
                pl.col("price_change_pct").cast(pl.Float64),
                pl.col("price_volatility_std").cast(pl.Float64),
                pl.col("extreme_movement").cast(pl.Boolean)
            ])
        
        return df
        
    except sqlite3.OperationalError as e:
        raise sqlite3.OperationalError(f"Database error: {e}")


def save_ecart_analysis_to_db(results_df: pl.DataFrame, db_path: str | Path = None) -> bool:
    """
    Save ecart type analysis results to the database.
    
    Args:
        results_df: DataFrame containing ecart type analysis results
        db_path: Path to SQLite database
        
    Returns:
        bool: True if successful, False otherwise
    """
    if db_path is None:
        db_path = Path(__file__).parent.parent / "scraper/component/scraperdb/data/ingestor.db"
    db_path = Path(db_path)
    
    try:
        with sqlite3.connect(str(db_path)) as con:
            # Clear existing data (optional - you might want to keep historical data)
            con.execute("DELETE FROM ecart_type_analysis")
            
            # Insert new results
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
    """
    Process ecart type analysis and save results to database.
    
    Returns:
        dict: Analysis results
    """
    try:
        # Load data from database
        df = load_data_from_db(db_path, limit)
        
        if df.height == 0:
            return {
                "success": False,
                "message": "No data available for analysis",
                "data": None
            }
        
        # Calculate écart type analysis
        results_df = build_ecart_type(df, period=period)
        
        if results_df.height == 0:
            return {
                "success": False,
                "message": "No analysis results generated",
                "data": None
            }
        
        # Save results to database
        saved = save_ecart_analysis_to_db(results_df, db_path)
        
        if not saved:
            print("Warning: Failed to save results to database, but analysis completed")
        
        # Generate summary for API response
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
    # Test the functions
    test_ecart_type()
