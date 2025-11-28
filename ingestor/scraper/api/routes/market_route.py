from fastapi import APIRouter, Query, HTTPException
from typing import Dict, Any
from datetime import datetime, timezone, timedelta
import mysql.connector
import os

from ..utils import JsonApiTemplate

router = APIRouter(
    prefix="/api",
    tags=["market"]
)

ApiResponse = JsonApiTemplate("api")

def get_db_connection():
    """Get MySQL database connection"""
    try:
        connection = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", "host.docker.internal"),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", ""),
            database=os.getenv("MYSQL_DATABASE", "ingestor")
        )
        return connection
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"MySQL connection error: {err}")


def _fetch_top_gainers_data(limit: int) -> Dict[str, Any]:
    con = get_db_connection()
    try:
        cursor = con.cursor()
        query = '''
        WITH price_changes AS (
            SELECT 
                a1.symbol,
                a1.name,
                a1.price as current_price,
                a1.market_cap,
                a1.fetched_at as current_date,
                LAG(a1.price) OVER (PARTITION BY a1.symbol ORDER BY a1.fetched_at) as prev_price,
                CASE 
                    WHEN LAG(a1.price) OVER (PARTITION BY a1.symbol ORDER BY a1.fetched_at) IS NOT NULL 
                    THEN ((a1.price - LAG(a1.price) OVER (PARTITION BY a1.symbol ORDER BY a1.fetched_at)) / LAG(a1.price) OVER (PARTITION BY a1.symbol ORDER BY a1.fetched_at)) * 100
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
        LIMIT %s
        '''
        
        cursor.execute(query, (limit,))
        results = cursor.fetchall()
        gainers = []
        total_volume = 0
        total_gain = 0
        best_gainer = None
        
        for i, row in enumerate(results):
            symbol, name, price, delta_pct, market_cap, date_end = row
            gainers.append({
                "rank": i + 1,
                "symbol": symbol,
                "name": name or symbol,
                "price": f"${price:.2f}" if price else "$0.00",
                "change_24h": f"+{delta_pct:.2f}%" if delta_pct else "+0.00%",
                "change_24h_value": delta_pct or 0,
                "market_cap": market_cap or 0,
                "last_updated": date_end
            })
            if market_cap:
                total_volume += market_cap
            if delta_pct:
                total_gain += delta_pct
                if best_gainer is None or delta_pct > best_gainer["change"]:
                    best_gainer = {"symbol": symbol, "change": delta_pct}
        
        avg_gain = total_gain / len(results) if results else 0
        return {
            "gainers": gainers,
            "summary": {
                "best_gainer": f"{best_gainer['symbol']} (+{best_gainer['change']:.2f}%)" if best_gainer else "N/A",
                "total_volume": f"${total_volume/1e9:.2f}B" if total_volume > 0 else "$0.00B",
                "average_gain": f"+{avg_gain:.2f}%"
            },
            "metadata": {
                "count": len(gainers),
                "window": "24h",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
    finally:
        con.close()


def _fetch_top_losers_data(limit: int) -> Dict[str, Any]:
    con = get_db_connection()
    try:
        cursor = con.cursor()
        query = '''
        WITH price_changes AS (
            SELECT 
                a1.symbol,
                a1.name,
                a1.price as current_price,
                a1.market_cap,
                a1.fetched_at as current_date,
                LAG(a1.price) OVER (PARTITION BY a1.symbol ORDER BY a1.fetched_at) as prev_price,
                CASE 
                    WHEN LAG(a1.price) OVER (PARTITION BY a1.symbol ORDER BY a1.fetched_at) IS NOT NULL 
                    THEN ((a1.price - LAG(a1.price) OVER (PARTITION BY a1.symbol ORDER BY a1.fetched_at)) / LAG(a1.price) OVER (PARTITION BY a1.symbol ORDER BY a1.fetched_at)) * 100
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
        LIMIT %s
        '''
        
        cursor.execute(query, (limit,))
        results = cursor.fetchall()
        losers = []
        total_volume = 0
        total_loss = 0
        worst_loser = None
        
        for i, row in enumerate(results):
            symbol, name, price, delta_pct, market_cap, date_end = row
            losers.append({
                "rank": i + 1,
                "symbol": symbol,
                "name": name or symbol,
                "price": f"${price:.2f}" if price else "$0.00",
                "change_24h": f"{delta_pct:.2f}%" if delta_pct else "0.00%",
                "change_24h_value": delta_pct or 0,
                "market_cap": market_cap or 0,
                "last_updated": date_end
            })
            if market_cap:
                total_volume += market_cap
            if delta_pct:
                total_loss += abs(delta_pct)
                if worst_loser is None or delta_pct < worst_loser["change"]:
                    worst_loser = {"symbol": symbol, "change": delta_pct}
        
        avg_loss = -total_loss / len(results) if results else 0
        return {
            "losers": losers,
            "summary": {
                "worst_loser": f"{worst_loser['symbol']} ({worst_loser['change']:.2f}%)" if worst_loser else "N/A",
                "total_volume": f"${total_volume/1e9:.2f}B" if total_volume > 0 else "$0.00B",
                "average_loss": f"{avg_loss:.2f}%"
            },
            "metadata": {
                "count": len(losers),
                "window": "24h",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
    finally:
        con.close()


def _fetch_market_overview_data() -> Dict[str, Any]:
    con = get_db_connection()
    try:
        cursor = con.cursor()
        major_cryptos_query = '''
        WITH latest_articles AS (
            SELECT 
                a.symbol,
                a.name,
                a.price,
                a.market_cap,
                a.fetched_at,
                ROW_NUMBER() OVER (PARTITION BY a.symbol ORDER BY a.fetched_at DESC) as rn
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
                ROW_NUMBER() OVER (PARTITION BY a.symbol ORDER BY a.fetched_at DESC) as rn
            FROM article a
            WHERE a.market_cap IS NOT NULL
        )
        SELECT SUM(market_cap) as total_market_cap
        FROM latest_articles
        WHERE rn = 1
        '''
        
        cursor.execute(major_cryptos_query)
        crypto_results = cursor.fetchall()
        cursor.execute(total_market_cap_query)
        total_cap_result = cursor.fetchone()
        
        cryptos = []
        for row in crypto_results:
            symbol, name, price, market_cap, change_24h = row
            cryptos.append({
                "symbol": symbol,
                "name": name or symbol,
                "price": f"${price:,.2f}" if price else "$0.00",
                "price_numeric": price or 0,
                "change_24h": f"{change_24h:+.1f}%" if change_24h != 0 else "0.0%",
                "change_24h_value": change_24h or 0,
                "market_cap": market_cap or 0
            })
        
        total_market_cap = total_cap_result[0] if total_cap_result and total_cap_result[0] else 0
        market_cap_change = 0.8
        
        return {
            "major_cryptos": cryptos,
            "total_market_cap": f"${total_market_cap/1e12:.2f}T" if total_market_cap > 0 else "$0.00T",
            "market_cap_change": f"+{market_cap_change:.1f}%",
            "market_cap_change_value": market_cap_change,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
    finally:
        con.close()


def _fetch_market_stats_data() -> Dict[str, Any]:
    con = get_db_connection()
    try:
        cursor = con.cursor()
        sources_query = '''
        SELECT COUNT(DISTINCT 
            CASE 
                WHEN url LIKE '%coinmarketcap%' THEN 'coinmarketcap'
                WHEN url LIKE '%coingecko%' THEN 'coingecko'
                WHEN url LIKE '%binance%' THEN 'binance'
                WHEN url LIKE '%crypto%' THEN 'crypto_news'
                ELSE SUBSTRING_INDEX(url, '/', 3)
            END
        ) as unique_sources
        FROM article 
        WHERE url IS NOT NULL
        '''
        
        today_articles_query = '''
        SELECT COUNT(*) as daily_articles
        FROM article 
        WHERE DATE(fetched_at) = CURDATE()
        '''
        
        yesterday_articles_query = '''
        SELECT COUNT(*) as yesterday_articles
        FROM article 
        WHERE DATE(fetched_at) = DATE_SUB(CURDATE(), INTERVAL 1 DAY)
        '''
        
        month_articles_query = '''
        SELECT COUNT(*) as month_articles
        FROM article 
        WHERE DATE_FORMAT(fetched_at, '%Y-%m') = DATE_FORMAT(NOW(), '%Y-%m')
        '''
        
        total_articles_query = '''
        SELECT COUNT(*) as total_articles
        FROM article
        '''
        
        symbols_query = '''
        SELECT COUNT(DISTINCT symbol) as symbols_tracked
        FROM article
        WHERE symbol IS NOT NULL
        '''
        
        cursor.execute(sources_query)
        sources_result = cursor.fetchone()
        cursor.execute(today_articles_query)
        today_result = cursor.fetchone()
        cursor.execute(yesterday_articles_query)
        yesterday_result = cursor.fetchone()
        cursor.execute(month_articles_query)
        month_result = cursor.fetchone()
        cursor.execute(total_articles_query)
        total_articles_result = cursor.fetchone()
        cursor.execute(symbols_query)
        symbols_result = cursor.fetchone()
        
        sources_count = sources_result[0] if sources_result else 0
        daily_articles = today_result[0] if today_result else 0
        yesterday_articles = yesterday_result[0] if yesterday_result else 0
        month_articles = month_result[0] if month_result else 0
        total_articles = total_articles_result[0] if total_articles_result else 0
        symbols_tracked = symbols_result[0] if symbols_result else 0
        
        articles_change = 0
        if yesterday_articles > 0:
            articles_change = ((daily_articles - yesterday_articles) / yesterday_articles) * 100
        elif daily_articles > 0:
            articles_change = 100
        
        month_change = 2
        
        return {
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
            "totals": {
                "articles": total_articles,
                "symbols": symbols_tracked
            },
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
    finally:
        con.close()

@router.get("/crypto/gainers")
async def get_top_gainers(
    limit: int = Query(5, ge=1, le=50, description="Number of top gainers to return"),
    window: str = Query("24h", description="Time window (24h, 7d, 30d)")
):
    try:
        response_data = _fetch_top_gainers_data(limit)
        response_data["metadata"]["window"] = window

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

@router.get("/crypto/losers")
async def get_top_losers(
    limit: int = Query(5, ge=1, le=50, description="Number of top losers to return"),
    window: str = Query("24h", description="Time window (24h, 7d, 30d)")
):
    try:
        response_data = _fetch_top_losers_data(limit)
        response_data["metadata"]["window"] = window

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

@router.get("/market/overview")
async def get_market_overview():
    try:
        response_data = _fetch_market_overview_data()
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

@router.get("/market/stats")
async def get_market_stats():
    try:
        response_data = _fetch_market_stats_data()
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


def _compute_trending_symbols(limit: int, window_hours: int) -> Dict[str, Any]:
    con = get_db_connection()
    try:
        now = datetime.now(timezone.utc)
        current_end = now
        current_start = now - timedelta(hours=window_hours)
        prev_end = current_start
        prev_start = prev_end - timedelta(hours=window_hours)

        def format_ts(value: datetime) -> str:
            return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

        def fetch_counts(start: datetime, end: datetime) -> Dict[str, int]:
            cursor = con.cursor()
            cursor.execute(
                """
                SELECT symbol_upper, COUNT(*) as cnt
                FROM (
                    SELECT COALESCE(UPPER(symbol), 'UNKNOWN') as symbol_upper
                    FROM article
                    WHERE symbol IS NOT NULL
                      AND fetched_at >= %s AND fetched_at < %s
                ) AS subquery
                GROUP BY symbol_upper
                """,
                (
                    format_ts(start),
                    format_ts(end)
                )
            )
            return {row[0]: row[1] for row in cursor.fetchall()}

        current_counts = fetch_counts(current_start, current_end)
        prev_counts = fetch_counts(prev_start, prev_end)

        trending = []
        for symbol, value in current_counts.items():
            previous = prev_counts.get(symbol, 0)
            if value == 0 and previous == 0:
                continue
            delta = value - previous
            if previous == 0:
                delta_pct = 100.0 if value > 0 else 0.0
            else:
                delta_pct = (delta / previous) * 100.0
            trending.append({
                "source": symbol,
                "value": value,
                "previous": previous,
                "delta": delta,
                "delta_pct": delta_pct
            })

        trending.sort(key=lambda item: (abs(item["delta_pct"]), item["value"]), reverse=True)
        return {
            "trending": trending[:limit],
            "metadata": {
                "window_hours": window_hours,
                "generated_at": now.isoformat(),
                "current_range": {
                    "start": current_start.isoformat(),
                    "end": current_end.isoformat()
                },
                "previous_range": {
                    "start": prev_start.isoformat(),
                    "end": prev_end.isoformat()
                }
            }
        }
    finally:
        con.close()


@router.get("/market/trending")
async def get_market_trending(
    window: str = Query("1h", description="Window size (1h, 4h, 12h, 1d, 3d, 7d)"),
    limit: int = Query(5, ge=1, le=50, description="Number of entries to return")
):
    window_map = {
        "1h": 1,
        "4h": 4,
        "12h": 12,
        "1d": 24,
        "3d": 72,
        "7d": 168
    }
    if window not in window_map:
        allowed = ", ".join(window_map.keys())
        raise HTTPException(status_code=400, detail=f"Invalid window '{window}'. Allowed values: {allowed}")

    try:
        data = _compute_trending_symbols(limit, window_map[window])
        response_data = {
            "window": window,
            "baseline": "previous_window",
            "trending": data.get("trending", []),
            "metadata": data.get("metadata", {})
        }
        return ApiResponse._create_response(
            level="info",
            msg="Market trending data computed successfully",
            response={
                "status": 200,
                "data": response_data
            }
        )
    except Exception as e:
        return ApiResponse._create_response(
            level="error",
            msg="Error while computing market trending data",
            response={
                "status": 500,
                "error": str(e)
            }
        )


@router.get("/market/home")
async def get_market_home(
    limit: int = Query(5, ge=1, le=50, description="Number of movers to display")
):
    try:
        overview = _fetch_market_overview_data()
        stats = _fetch_market_stats_data()
        gainers = _fetch_top_gainers_data(limit)
        losers = _fetch_top_losers_data(limit)
        
        response_data = {
            "overview": overview,
            "stats": stats,
            "gainers": gainers.get("gainers", []),
            "gainers_summary": gainers.get("summary", {}),
            "losers": losers.get("losers", []),
            "losers_summary": losers.get("summary", {}),
            "metadata": {
                "requested_limit": limit,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
        }
        
        return ApiResponse._create_response(
            level="info",
            msg="Market home dashboard data retrieved successfully",
            response={
                "status": 200,
                "data": response_data
            }
        )
    except Exception as e:
        return ApiResponse._create_response(
            level="error",
            msg="Error while fetching market home dashboard",
            response={
                "status": 500,
                "error": str(e)
            }
        )