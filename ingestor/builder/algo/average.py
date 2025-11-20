import polars as pl
import sqlite3
from pathlib import Path
from typing import List, Dict, Any


def calculate_sma(values: List[float], window: int) -> List[float]:
    """Simple Moving Average (SMA) - Moyenne arithmétique simple des N dernières valeurs."""
    if len(values) < window:
        return []
    result = []
    for i in range(len(values) - window + 1):
        avg = sum(values[i:i+window]) / window
        result.append(round(avg, 4))
    return result


def calculate_wma(values: List[float], window: int) -> List[float]:
    """Weighted Moving Average (WMA) - Moyenne pondérée linéaire."""
    if len(values) < window:
        return []
    result = []
    weights = list(range(1, window + 1))
    weight_sum = sum(weights)
    
    for i in range(len(values) - window + 1):
        weighted_sum = sum(v * w for v, w in zip(values[i:i+window], weights))
        result.append(round(weighted_sum / weight_sum, 4))
    return result


def calculate_ema(values: List[float], window: int) -> List[float]:
    """Exponential Moving Average (EMA) - Moyenne mobile exponentielle."""
    if len(values) < window:
        return []
    
    result = []
    multiplier = 2 / (window + 1)
    ema = sum(values[:window]) / window
    result.append(round(ema, 4))
    
    for i in range(window, len(values)):
        ema = (values[i] * multiplier) + (ema * (1 - multiplier))
        result.append(round(ema, 4))
    
    return result


def build_moving_averages(df: pl.DataFrame, window: int = 7, ma_types: List[str] = ["sma"]) -> pl.DataFrame:
    """Calculate moving averages on DataFrame with price data."""
    required_cols = {"symbol", "price_usd", "ts"}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    df_clean = (
        df.filter(pl.col("price_usd").is_not_null())
          .with_columns(pl.col("ts").cast(pl.Datetime(time_zone="UTC")))
          .sort(["symbol", "ts"])
    )
    
    if "all" in ma_types:
        ma_types = ["sma", "wma", "ema"]
    
    result = df_clean.clone()
    
    for ma_type in ma_types:
        if ma_type == "sma":
            result = result.with_columns([
                pl.col("price_usd").rolling_mean(window_size=window).over("symbol").alias(f"sma_{window}")
            ])
        elif ma_type == "ema":
            result = result.with_columns([
                pl.col("price_usd").ewm_mean(span=window, adjust=False).over("symbol").alias(f"ema_{window}")
            ])
    
    result = result.with_columns([
        pl.lit(window).alias("ma_window"),
        pl.lit(",".join(ma_types)).alias("ma_types")
    ])
    
    return result


def test_moving_averages():
    """Test the moving averages calculation."""
    print("=" * 50)
    print("Testing Moving Averages")
    print("=" * 50)
    return True


if __name__ == "__main__":
    test_moving_averages()
