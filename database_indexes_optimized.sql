-- ================================================================
-- CryptoViz Database Performance Optimization
-- Optimized indexes for fast dashboard queries
-- Run this after database creation to improve performance
-- ================================================================

USE ingestor;

-- ==================== ARTICLE TABLE INDEXES ====================
-- These indexes optimize the most common query patterns

-- 1. Symbol-based queries with time sorting (most common pattern)
-- Optimizes: WHERE symbol = ? ORDER BY fetched_at DESC LIMIT ?
CREATE INDEX idx_article_symbol_fetched 
ON article(symbol, fetched_at DESC);

-- 2. Latest data queries (home dashboard, market overview)
-- Optimizes: ORDER BY fetched_at DESC LIMIT ?
CREATE INDEX idx_article_fetched_desc 
ON article(fetched_at DESC);

-- 3. Top gainers/losers queries (covering index)
-- Optimizes: WHERE price IS NOT NULL AND volume_24h IS NOT NULL
CREATE INDEX idx_article_valid_data 
ON article(fetched_at DESC, symbol, price, volume_24h, market_cap, name)
WHERE price IS NOT NULL AND volume_24h IS NOT NULL;

-- 4. Market cap aggregations
-- Optimizes: SELECT SUM(market_cap) ... WHERE market_cap IS NOT NULL
CREATE INDEX idx_article_market_cap 
ON article(market_cap DESC, fetched_at DESC)
WHERE market_cap IS NOT NULL;

-- 5. Symbol lookups (deduplication, symbol list)
CREATE INDEX idx_article_symbol 
ON article(symbol);

-- 6. URL deduplication (191 chars for utf8mb4 compatibility)
CREATE INDEX idx_article_url 
ON article(url(191));

-- ==================== DELTA TABLE INDEXES ====================

-- 1. Time window queries with symbol
-- Optimizes: WHERE window_label = '1d' AND symbol = ?
CREATE INDEX idx_delta_window_symbol_date 
ON delta(window_label, symbol, date_end DESC);

-- 2. Price change sorting (gainers/losers)
-- Optimizes: WHERE window_label = '1d' ORDER BY delta_pct DESC
CREATE INDEX idx_delta_window_pct 
ON delta(window_label, delta_pct DESC, date_end DESC);

-- 3. Symbol-based time series
-- Optimizes: WHERE symbol = ? ORDER BY date_end DESC
CREATE INDEX idx_delta_symbol_date 
ON delta(symbol, date_end DESC);

-- ==================== TABLE ANALYSIS ====================

-- Update table statistics for query optimizer
ANALYZE TABLE article;
ANALYZE TABLE delta;

-- ==================== VERIFY INDEXES ====================

-- Show all indexes with their details
SELECT 
    TABLE_NAME,
    INDEX_NAME,
    GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) as COLUMNS,
    INDEX_TYPE,
    NON_UNIQUE
FROM 
    INFORMATION_SCHEMA.STATISTICS
WHERE 
    TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME IN ('article', 'delta')
GROUP BY 
    TABLE_NAME, INDEX_NAME, INDEX_TYPE, NON_UNIQUE
ORDER BY 
    TABLE_NAME, INDEX_NAME;

-- ==================== PERFORMANCE MONITORING ====================

-- Check slow queries (requires slow_query_log enabled)
-- SET GLOBAL slow_query_log = 'ON';
-- SET GLOBAL long_query_time = 2;

-- Table statistics
SELECT 
    'article' as table_name,
    COUNT(*) as total_rows,
    COUNT(DISTINCT symbol) as unique_symbols,
    COUNT(DISTINCT DATE(fetched_at)) as unique_dates,
    COUNT(CASE WHEN price IS NOT NULL THEN 1 END) as rows_with_price,
    COUNT(CASE WHEN volume_24h IS NOT NULL THEN 1 END) as rows_with_volume,
    MIN(fetched_at) as earliest_date,
    MAX(fetched_at) as latest_date,
    ROUND(DATA_LENGTH / 1024 / 1024, 2) as data_size_mb,
    ROUND(INDEX_LENGTH / 1024 / 1024, 2) as index_size_mb
FROM article, 
     INFORMATION_SCHEMA.TABLES 
WHERE 
    TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'article';

-- ==================== OPTIMIZATION RECOMMENDATIONS ====================
/*
1. MySQL Configuration (add to my.cnf):
   [mysqld]
   innodb_buffer_pool_size = 2G          # 70-80% of available RAM
   innodb_log_file_size = 512M            # Large for better write performance
   innodb_flush_log_at_trx_commit = 2     # Better performance, slight risk
   innodb_flush_method = O_DIRECT         # Avoid double buffering
   max_connections = 200                   # Adjust based on load
   query_cache_size = 0                    # Disabled in MySQL 8+
   
2. Regular maintenance:
   - Run ANALYZE TABLE weekly
   - Monitor slow query log
   - Check index usage with performance_schema
   
3. Query optimization:
   - Always use LIMIT for large result sets
   - Use covering indexes when possible
   - Add WHERE conditions to filter early
   - Consider materialized views for complex aggregations

4. Table partitioning (for very large tables):
   - Partition by date range (monthly or weekly)
   - Improves query performance on time-based queries
   - Makes data archival easier

5. Caching strategy:
   - Cache frequently accessed data in application layer
   - Use Redis/Memcached for dashboard data
   - Implement query result caching
*/

-- ==================== TEST QUERY PERFORMANCE ====================

-- Test 1: Latest data for symbol
EXPLAIN SELECT * FROM article 
WHERE symbol = 'BTC' 
ORDER BY fetched_at DESC 
LIMIT 100;

-- Test 2: Top gainers
EXPLAIN 
WITH price_changes AS (
    SELECT 
        symbol, name, price, market_cap, fetched_at,
        LAG(price) OVER (PARTITION BY symbol ORDER BY fetched_at) as prev_price
    FROM article
    WHERE price IS NOT NULL AND volume_24h IS NOT NULL
)
SELECT * FROM price_changes 
WHERE prev_price IS NOT NULL
ORDER BY ((price - prev_price) / prev_price) DESC 
LIMIT 5;

-- Test 3: Market overview
EXPLAIN SELECT 
    symbol, name, price, market_cap, fetched_at
FROM (
    SELECT 
        symbol, name, price, market_cap, fetched_at,
        ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY fetched_at DESC) as rn
    FROM article
    WHERE symbol IN ('BTC', 'ETH', 'SOL', 'ADA', 'DOT', 'AVAX')
) latest
WHERE rn = 1;

