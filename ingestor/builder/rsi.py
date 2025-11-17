import polars as pl
import sqlite3
from pathlib import Path


def build_rsi(df: pl.DataFrame, period: int = 14) -> pl.DataFrame:
    """
    Calculate the Relative Strength Index (RSI) for price movements.
    
    RSI is a momentum oscillator that measures the speed and change of price movements.
    It oscillates between zero and 100. Traditionally, RSI is considered overbought when 
    above 70 and oversold when below 30.
    
    Args:
        df: DataFrame with columns 'symbol', 'price_usd', and 'ts' (timestamp)
        period: Period for RSI calculation (default: 14)
        
    Returns:
        DataFrame with additional RSI-related columns
    """
    # Ensure we have the required columns
    required_cols = {"symbol", "price_usd", "ts"}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    df_clean = (
        df.filter(pl.col("price_usd").is_not_null())
          .with_columns(pl.col("ts").cast(pl.Datetime(time_zone="UTC")))
          .sort(["symbol", "ts"])
    )
    
    result = (
        df_clean
        .with_columns([
            # Calculate price changes
            pl.col("price_usd").diff().over("symbol").alias("price_change"),
            pl.col("price_usd").pct_change().over("symbol").alias("price_change_pct")
        ])
        .with_columns([
            # Separate gains and losses
            pl.when(pl.col("price_change") > 0)
              .then(pl.col("price_change"))
              .otherwise(0.0)
              .alias("gain"),
            pl.when(pl.col("price_change") < 0)
              .then(pl.col("price_change").abs())
              .otherwise(0.0)
              .alias("loss")
        ])
        .with_columns([
            # Calculate average gains and losses using SMA (Simple Moving Average)
            pl.col("gain")
              .rolling_mean(window_size=period)
              .over("symbol")
              .alias("avg_gain"),
            pl.col("loss")
              .rolling_mean(window_size=period)
              .over("symbol")
              .alias("avg_loss")
        ])
        .with_columns([
            # Calculate RS (Relative Strength) and RSI
            (pl.col("avg_gain") / pl.col("avg_loss")).alias("rs"),
            (100 - (100 / (1 + (pl.col("avg_gain") / pl.col("avg_loss"))))).alias("rsi")
        ])
        .with_columns([
            # RSI signal interpretation
            pl.when(pl.col("rsi") >= 70)
              .then(pl.lit("overbought"))
              .when(pl.col("rsi") <= 30)
              .then(pl.lit("oversold"))
              .otherwise(pl.lit("neutral"))
              .alias("rsi_signal"),
            
            # RSI strength categories
            pl.when(pl.col("rsi") >= 80)
              .then(pl.lit("very_strong_buy"))
              .when(pl.col("rsi") >= 70)
              .then(pl.lit("strong_buy"))
              .when(pl.col("rsi") >= 50)
              .then(pl.lit("bullish"))
              .when(pl.col("rsi") >= 30)
              .then(pl.lit("bearish"))
              .when(pl.col("rsi") >= 20)
              .then(pl.lit("strong_sell"))
              .otherwise(pl.lit("very_strong_sell"))
              .alias("rsi_strength"),
            
            # RSI momentum change
            (pl.col("rsi") - pl.col("rsi").shift(1).over("symbol")).alias("rsi_momentum"),
            
            # Period used for calculation
            pl.lit(period).alias("rsi_period")
        ])
    )
    
    return result


def load_data_from_db(db_path: str | Path = None, limit: int = 1000) -> pl.DataFrame:
    """Load data from SQLite database for RSI analysis."""
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

        df = df.with_columns([
            pl.col("price_usd").cast(pl.Float64),
            pl.col("ts").str.to_datetime(format="%Y-%m-%d %H:%M:%S", time_zone="UTC")
        ])

        return df

    except sqlite3.OperationalError as e:
        raise sqlite3.OperationalError(f"Database error: {e}")


def calculate_rsi_analysis(period: int = 14, limit: int = 1000, db_path: str | Path = None) -> dict:
    """Calculate comprehensive RSI analysis for all symbols."""
    df = load_data_from_db(db_path, limit)
    
    if df.height == 0:
        return {
            "success": False,
            "message": "No data available",
            "data": None
        }
    
    results = build_rsi(df, period=period)
    
    # Summary statistics by symbol
    summary = (
        results
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
    
    # Latest RSI data for each symbol
    latest_data = (
        results
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
    
    return {
        "success": True,
        "message": "RSI analysis completed successfully",
        "metadata": {
            "period": period,
            "total_records": results.height,
            "symbols_analyzed": results["symbol"].n_unique(),
            "analysis_timestamp": results["ts"].max() if results.height > 0 else None
        },
        "summary": summary.to_dicts(),
        "latest_data": latest_data.to_dicts(),
        "detailed_results": results.to_dicts() if results.height <= 1000 else None
    }


def get_symbol_rsi_analysis(symbol: str, period: int = 14, limit: int = 1000, db_path: str | Path = None) -> dict:
    """Get RSI analysis for a specific symbol."""
    df = load_data_from_db(db_path, limit)
    
    if df.height == 0:
        return {
            "success": False,
            "message": "No data available",
            "data": None
        }
    
    symbol_df = df.filter(pl.col("symbol") == symbol.upper())
    
    if symbol_df.height == 0:
        return {
            "success": False,
            "message": f"No data found for symbol {symbol}",
            "data": None
        }
    
    results = build_rsi(symbol_df, period=period)
    
    if results.height == 0:
        return {
            "success": False,
            "message": f"No RSI analysis results for symbol {symbol}",
            "data": None
        }
    
    # Time series data for charts
    time_series = (
        results
        .filter(pl.col("rsi").is_not_null())
        .select([
            "ts", "price_usd", "price_change_pct", 
            "rsi", "rsi_signal", "rsi_strength", 
            "rsi_momentum", "avg_gain", "avg_loss"
        ])
        .sort("ts")
    )
    
    # Latest statistics
    latest = results.tail(1).select([
        "price_usd", "rsi", "rsi_signal", "rsi_strength",
        "rsi_momentum", "avg_gain", "avg_loss"
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


def load_saved_rsi_analysis(db_path: str | Path = None, limit: int = 1000) -> pl.DataFrame:
    """Load saved RSI analysis from database."""
    if db_path is None:
        db_path = Path(__file__).parent.parent / "scraper/component/scraperdb/data/ingestor.db"
    db_path = Path(db_path)
    
    if not db_path.exists():
        raise FileNotFoundError(f"SQLite DB not found at {db_path}")
    
    query = '''
    SELECT 
        symbol, timestamp as ts, price_usd, price_change, price_change_pct,
        gain, loss, avg_gain, avg_loss, rs, rsi, rsi_signal, rsi_strength,
        rsi_momentum, rsi_period, created_at
    FROM rsi_analysis
    ORDER BY symbol, timestamp
    LIMIT ?
    '''
    
    try:
        with sqlite3.connect(str(db_path)) as con:
            df = pl.read_database(query, con, execute_options={"parameters": [limit]})
        
        if df.height > 0:
            df = df.with_columns([
                pl.col("ts").str.to_datetime(format="%Y-%m-%d %H:%M:%S", time_zone="UTC"),
                pl.col("price_usd").cast(pl.Float64),
                pl.col("rsi").cast(pl.Float64)
            ])
        
        return df
        
    except sqlite3.OperationalError as e:
        raise sqlite3.OperationalError(f"Database error: {e}")


def save_rsi_analysis_to_db(results_df: pl.DataFrame, db_path: str | Path = None) -> bool:
    """Save RSI analysis results to database."""
    if db_path is None:
        db_path = Path(__file__).parent.parent / "scraper/component/scraperdb/data/ingestor.db"
    db_path = Path(db_path)
    
    try:
        with sqlite3.connect(str(db_path)) as con:
            # Create table if it doesn't exist
            con.execute("""
                CREATE TABLE IF NOT EXISTS rsi_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    price_usd REAL,
                    price_change REAL,
                    price_change_pct REAL,
                    gain REAL,
                    loss REAL,
                    avg_gain REAL,
                    avg_loss REAL,
                    rs REAL,
                    rsi REAL,
                    rsi_signal TEXT,
                    rsi_strength TEXT,
                    rsi_momentum REAL,
                    rsi_period INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, timestamp)
                )
            """)
            
            # Clear existing data
            con.execute("DELETE FROM rsi_analysis")
            
            # Insert new data
            for row in results_df.to_dicts():
                con.execute("""
                    INSERT OR REPLACE INTO rsi_analysis (
                        symbol, timestamp, price_usd, price_change, price_change_pct,
                        gain, loss, avg_gain, avg_loss, rs, rsi, rsi_signal,
                        rsi_strength, rsi_momentum, rsi_period, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """, (
                    row.get('symbol'),
                    row.get('ts'),
                    row.get('price_usd'),
                    row.get('price_change'),
                    row.get('price_change_pct'),
                    row.get('gain'),
                    row.get('loss'),
                    row.get('avg_gain'),
                    row.get('avg_loss'),
                    row.get('rs'),
                    row.get('rsi'),
                    row.get('rsi_signal'),
                    row.get('rsi_strength'),
                    row.get('rsi_momentum'),
                    row.get('rsi_period')
                ))
            
            con.commit()
            print(f"Successfully saved {results_df.height} RSI analysis records to database")
            return True
            
    except Exception as e:
        print(f"Error saving RSI analysis to database: {e}")
        return False


def process_and_save_rsi_analysis(period: int = 14, limit: int = 1000, db_path: str | Path = None) -> dict:
    """Process and save RSI analysis for all symbols."""
    try:
        df = load_data_from_db(db_path, limit)
        
        if df.height == 0:
            return {
                "success": False,
                "message": "No data available for RSI analysis",
                "data": None
            }
        
        results_df = build_rsi(df, period=period)
        
        if results_df.height == 0:
            return {
                "success": False,
                "message": "No RSI analysis results generated",
                "data": None
            }
        
        saved = save_rsi_analysis_to_db(results_df, db_path)
        
        if not saved:
            print("Warning: Failed to save results to database, but analysis completed")
        
        analysis_results = calculate_rsi_analysis(period=period, limit=limit, db_path=db_path)
        
        print("RSI analysis completed successfully")
        print(f"Analyzed {results_df['symbol'].n_unique()} symbols")
        print(f"Total records: {results_df.height}")
        print(f"Results saved to database: {saved}")
        
        return analysis_results
        
    except Exception as e:
        print(f"Error processing RSI analysis: {e}")
        return {
            "success": False,
            "message": f"RSI analysis failed: {str(e)}",
            "data": None
        }


if __name__ == "__main__":
    analysis_results = process_and_save_rsi_analysis()
    print(f"RSI Analysis completed: {analysis_results['success']}")
    if analysis_results['success']:
        print(f"Message: {analysis_results['message']}")
        if 'summary' in analysis_results:
            print(f"Symbols analyzed: {len(analysis_results['summary'])}")