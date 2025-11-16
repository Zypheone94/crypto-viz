from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import sqlite3
import os
from pathlib import Path

from ..utils import JsonApiTemplate

def _resolve(path: Path) -> Path:
    if path.is_absolute():
        return path
    return (Path.cwd() / path).resolve()

DB_PATH = _resolve(Path("component/scraperdb/data/ingestor.db"))

router = APIRouter(
    prefix="/market",
    tags=["market"]
)

ApiResponse = JsonApiTemplate("api")

def get_db_connection():
    """Get database connection"""
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=500, detail="Database not found")
    return sqlite3.connect(DB_PATH)

@router.get("/api/market/top-gainers")
async def get_top_gainers(
    limit: int = Query(5, ge=1, le=50, description="Number of top gainers to return"),
    window: str = Query("24h", description="Time window (24h, 7d, 30d)")
):
    try:
        con = get_db_connection()
        cursor = con.cursor()
        query = '''
        WITH price_changes AS (
            SELECT 
                a1.symbol,
                a1.name,
                a1.price as current_price,
                a1.market_cap,
                a1.date as current_date,
                LAG(a1.price, 1) OVER (PARTITION BY a1.symbol ORDER BY a1.date) as prev_price,
                CASE 
                    WHEN LAG(a1.price, 1) OVER (PARTITION BY a1.symbol ORDER BY a1.date) IS NOT NULL 
                    THEN ((a1.price - LAG(a1.price, 1) OVER (PARTITION BY a1.symbol ORDER BY a1.date)) / LAG(a1.price, 1) OVER (PARTITION BY a1.symbol ORDER BY a1.date)) * 100
                    ELSE 0
                END as price_change_pct
            FROM article a1
        ),
        latest_data AS (
            SELECT 
                symbol,
                name,
                current_price,
                market_cap,
                price_change_pct,
                current_date,
                ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY current_date DESC) as rn
            FROM price_changes
            WHERE price_change_pct > 0
        )
        SELECT 
            symbol,
            name,
            current_price,
            price_change_pct,
            market_cap,
            current_date
        FROM latest_data
        WHERE rn = 1
        ORDER BY price_change_pct DESC
        LIMIT ?
        '''
        
        results = cursor.execute(query, (limit,)).fetchall()
        
        gainers = []
        total_volume = 0
        total_gain = 0
        best_gainer = None
        
        for i, row in enumerate(results):
            symbol, name, price, delta_pct, market_cap, date_end = row
            
            gainer_data = {
                "rank": i + 1,
                "symbol": symbol,
                "name": name or symbol,
                "price": f"${price:.2f}" if price else "$0.00",
                "change_24h": f"+{delta_pct:.2f}%" if delta_pct else "+0.00%",
                "change_24h_value": delta_pct or 0,
                "market_cap": market_cap or 0,
                "last_updated": date_end
            }
            
            gainers.append(gainer_data)
            
            if market_cap:
                total_volume += market_cap
            if delta_pct:
                total_gain += delta_pct
                if best_gainer is None or delta_pct > best_gainer["change"]:
                    best_gainer = {"symbol": symbol, "change": delta_pct}
        
        avg_gain = total_gain / len(results) if results else 0
        
        response_data = {
            "gainers": gainers,
            "summary": {
                "best_gainer": f"{best_gainer['symbol']} (+{best_gainer['change']:.2f}%)" if best_gainer else "N/A",
                "total_volume": f"${total_volume/1e9:.2f}B" if total_volume > 0 else "$0.00B",
                "average_gain": f"+{avg_gain:.2f}%"
            },
            "metadata": {
                "count": len(gainers),
                "window": window,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        
        con.close()
        
        return ApiResponse._create_response(
            level="info",
            msg="Top crypto gainers retrieved successfully",
            response={
                "status": 200,
                "data": response_data
            }
        )
        
    except Exception as e:
        return ApiResponse._create_response(
            level="error",
            msg="Error while fetching top gainers",
            response={
                "status": 500,
                "error": str(e)
            }
        )

@router.get("/api/market/top-losers")
async def get_top_losers(
    limit: int = Query(5, ge=1, le=50, description="Number of top losers to return"),
    window: str = Query("24h", description="Time window (24h, 7d, 30d)")
):
    try:
        con = get_db_connection()
        cursor = con.cursor()
        query = '''
        WITH price_changes AS (
            SELECT 
                a1.symbol,
                a1.name,
                a1.price as current_price,
                a1.market_cap,
                a1.date as current_date,
                LAG(a1.price, 1) OVER (PARTITION BY a1.symbol ORDER BY a1.date) as prev_price,
                CASE 
                    WHEN LAG(a1.price, 1) OVER (PARTITION BY a1.symbol ORDER BY a1.date) IS NOT NULL 
                    THEN ((a1.price - LAG(a1.price, 1) OVER (PARTITION BY a1.symbol ORDER BY a1.date)) / LAG(a1.price, 1) OVER (PARTITION BY a1.symbol ORDER BY a1.date)) * 100
                    ELSE 0
                END as price_change_pct
            FROM article a1
        ),
        latest_data AS (
            SELECT 
                symbol,
                name,
                current_price,
                market_cap,
                price_change_pct,
                current_date,
                ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY current_date DESC) as rn
            FROM price_changes
            WHERE price_change_pct < 0
        )
        SELECT 
            symbol,
            name,
            current_price,
            price_change_pct,
            market_cap,
            current_date
        FROM latest_data
        WHERE rn = 1
        ORDER BY price_change_pct ASC
        LIMIT ?
        '''
        
        results = cursor.execute(query, (limit,)).fetchall()
        
        losers = []
        total_volume = 0
        total_loss = 0
        worst_loser = None
        
        for i, row in enumerate(results):
            symbol, name, price, delta_pct, market_cap, date_end = row
            
            loser_data = {
                "rank": i + 1,
                "symbol": symbol,
                "name": name or symbol,
                "price": f"${price:.2f}" if price else "$0.00",
                "change_24h": f"{delta_pct:.2f}%" if delta_pct else "0.00%",
                "change_24h_value": delta_pct or 0,
                "market_cap": market_cap or 0,
                "last_updated": date_end
            }
            
            losers.append(loser_data)
            
            if market_cap:
                total_volume += market_cap
            if delta_pct:
                total_loss += abs(delta_pct)
                if worst_loser is None or delta_pct < worst_loser["change"]:
                    worst_loser = {"symbol": symbol, "change": delta_pct}
        
        avg_loss = -total_loss / len(results) if results else 0
        
        response_data = {
            "losers": losers,
            "summary": {
                "worst_loser": f"{worst_loser['symbol']} ({worst_loser['change']:.2f}%)" if worst_loser else "N/A",
                "total_volume": f"${total_volume/1e9:.2f}B" if total_volume > 0 else "$0.00B",
                "average_loss": f"{avg_loss:.2f}%"
            },
            "metadata": {
                "count": len(losers),
                "window": window,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        
        con.close()
        
        return ApiResponse._create_response(
            level="info",
            msg="Top crypto losers retrieved successfully",
            response={
                "status": 200,
                "data": response_data
            }
        )
        
    except Exception as e:
        return ApiResponse._create_response(
            level="error",
            msg="Error while fetching top losers",
            response={
                "status": 500,
                "error": str(e)
            }
        )

@router.get("/api/market/overview")
async def get_market_overview():
    try:
        con = get_db_connection()
        cursor = con.cursor()
        major_cryptos_query = '''
        WITH latest_articles AS (
            SELECT 
                a.symbol,
                a.name,
                a.price,
                a.market_cap,
                a.date,
                ROW_NUMBER() OVER (PARTITION BY a.symbol ORDER BY a.date DESC) as rn
            FROM article a
            WHERE a.symbol IN ('BTC', 'ETH', 'SOL', 'ADA', 'DOT', 'AVAX')
        ),
        latest_deltas AS (
            SELECT 
                d.symbol,
                d.delta_pct,
                ROW_NUMBER() OVER (PARTITION BY d.symbol ORDER BY d.date_end DESC) as rn
            FROM delta d
            WHERE d.window_label = '1d'
        )
        SELECT 
            la.symbol,
            la.name,
            la.price,
            la.market_cap,
            COALESCE(ld.delta_pct, 0) as change_24h
        FROM latest_articles la
        LEFT JOIN latest_deltas ld ON la.symbol = ld.symbol AND ld.rn = 1
        WHERE la.rn = 1
        ORDER BY la.market_cap DESC
        '''
        
        total_market_cap_query = '''
        WITH latest_articles AS (
            SELECT 
                a.symbol,
                a.market_cap,
                ROW_NUMBER() OVER (PARTITION BY a.symbol ORDER BY a.date DESC) as rn
            FROM article a
            WHERE a.market_cap IS NOT NULL
        )
        SELECT SUM(market_cap) as total_market_cap
        FROM latest_articles
        WHERE rn = 1
        '''
        
        crypto_results = cursor.execute(major_cryptos_query).fetchall()
        total_cap_result = cursor.execute(total_market_cap_query).fetchone()
        
        cryptos = []
        for row in crypto_results:
            symbol, name, price, market_cap, change_24h = row
            crypto_data = {
                "symbol": symbol,
                "name": name or symbol,
                "price": f"${price:,.2f}" if price else "$0.00",
                "change_24h": f"{change_24h:+.1f}%" if change_24h != 0 else "0.0%",
                "change_24h_value": change_24h or 0,
                "market_cap": market_cap or 0
            }
            cryptos.append(crypto_data)
        
        total_market_cap = total_cap_result[0] if total_cap_result and total_cap_result[0] else 0
        
        market_cap_change = 0.8
        
        response_data = {
            "major_cryptos": cryptos,
            "total_market_cap": f"${total_market_cap/1e12:.2f}T" if total_market_cap > 0 else "$0.00T",
            "market_cap_change": f"+{market_cap_change:.1f}%",
            "market_cap_change_value": market_cap_change,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        
        con.close()
        
        return ApiResponse._create_response(
            level="info",
            msg="Market overview retrieved successfully",
            response={
                "status": 200,
                "data": response_data
            }
        )
        
    except Exception as e:
        return ApiResponse._create_response(
            level="error",
            msg="Error while fetching market overview",
            response={
                "status": 500,
                "error": str(e)
            }
        )

@router.get("/api/market/stats")
async def get_market_stats():
    try:
        con = get_db_connection()
        cursor = con.cursor()
        sources_query = '''
        SELECT COUNT(DISTINCT 
            CASE 
                WHEN url LIKE '%coinmarketcap%' THEN 'coinmarketcap'
                WHEN url LIKE '%coingecko%' THEN 'coingecko'
                WHEN url LIKE '%binance%' THEN 'binance'
                WHEN url LIKE '%crypto%' THEN 'crypto_news'
                ELSE SUBSTR(url, 1, INSTR(url, '/') + INSTR(SUBSTR(url, INSTR(url, '/') + 1), '/'))
            END
        ) as unique_sources
        FROM article 
        WHERE url IS NOT NULL
        '''
        
        today_articles_query = '''
        SELECT COUNT(*) as daily_articles
        FROM article 
        WHERE DATE(date) = DATE('now')
        '''
        
        yesterday_articles_query = '''
        SELECT COUNT(*) as yesterday_articles
        FROM article 
        WHERE DATE(date) = DATE('now', '-1 day')
        '''
        
        month_articles_query = '''
        SELECT COUNT(*) as month_articles
        FROM article 
        WHERE strftime('%Y-%m', date) = strftime('%Y-%m', 'now')
        '''
        
        sources_result = cursor.execute(sources_query).fetchone()
        today_result = cursor.execute(today_articles_query).fetchone()
        yesterday_result = cursor.execute(yesterday_articles_query).fetchone()
        month_result = cursor.execute(month_articles_query).fetchone()
        
        sources_count = sources_result[0] if sources_result else 0
        daily_articles = today_result[0] if today_result else 0
        yesterday_articles = yesterday_result[0] if yesterday_result else 0
        month_articles = month_result[0] if month_result else 0
        
        articles_change = 0
        if yesterday_articles > 0:
            articles_change = ((daily_articles - yesterday_articles) / yesterday_articles) * 100
        elif daily_articles > 0:
            articles_change = 100
        
        month_change = 2
        
        response_data = {
            "crypto_sources": {
                "count": sources_count,
                "change_month": f"+{month_change}",
                "description": "Plateformes et médias surveillés"
            },
            "daily_articles": {
                "count": daily_articles,
                "change_yesterday": f"{articles_change:+.0f}% vs hier" if articles_change != 0 else "0% vs hier",
                "change_yesterday_value": articles_change,
                "description": "Nouvelles collectées aujourd'hui"
            },
            "monthly_articles": month_articles,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        
        con.close()
        
        return ApiResponse._create_response(
            level="info",
            msg="Market statistics retrieved successfully",
            response={
                "status": 200,
                "data": response_data
            }
        )
        
    except Exception as e:
        return ApiResponse._create_response(
            level="error",
            msg="Error while fetching market statistics",
            response={
                "status": 500,
                "error": str(e)
            }
        )