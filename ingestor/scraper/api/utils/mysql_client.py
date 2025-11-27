"""MySQL client utilities for executing queries with Polars DataFrame results."""

import mysql.connector
import polars as pl
import os
from typing import List, Any, Optional


def get_mysql_connection():
    """Get a MySQL database connection."""
    try:
        connection = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", "host.docker.internal"),
            user=os.getenv("MYSQL_USER", "admin"),
            password=os.getenv("MYSQL_PASSWORD", "admin"),
            database=os.getenv("MYSQL_DATABASE", "crypto_viz")
        )
        return connection
    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL: {err}")
        return None


def execute_query_polars(query: str, params: Optional[List[Any]] = None) -> pl.DataFrame:
    """
    Execute a MySQL query and return results as a Polars DataFrame.
    
    Args:
        query: SQL query string with placeholders (%s)
        params: List of parameters to substitute in query
    
    Returns:
        Polars DataFrame with query results
    """
    connection = get_mysql_connection()
    if not connection:
        return pl.DataFrame([])
    
    try:
        cursor = connection.cursor(dictionary=True)
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        results = cursor.fetchall()
        cursor.close()
        
        if not results:
            return pl.DataFrame([])
        
        # Convert to Polars DataFrame
        return pl.DataFrame(results)
        
    except mysql.connector.Error as err:
        print(f"Error executing query: {err}")
        return pl.DataFrame([])
        
    finally:
        if connection:
            connection.close()


def load_symbol_data(symbol: Optional[str] = None, limit: int = 1000) -> pl.DataFrame:
    """
    Load symbol data from the MySQL database.
    
    Args:
        symbol: Optional symbol filter
        limit: Maximum number of records to return
    
    Returns:
        Polars DataFrame with symbol data
    """
    query = """
    SELECT 
        symbol,
        price,
        volume_24h,
        fetched_at as ts,
        name,
        url
    FROM article 
    WHERE price IS NOT NULL 
      AND symbol IS NOT NULL
      AND volume_24h IS NOT NULL
    """
    
    params = []
    
    if symbol:
        query += " AND UPPER(symbol) = UPPER(%s)"
        params.append(symbol)
    
    query += " ORDER BY symbol, fetched_at LIMIT %s"
    params.append(limit)
    
    return execute_query_polars(query, params)