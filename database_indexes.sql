-- Database Performance Optimization Script
-- This script adds indexes to the MySQL ingestor database for better query performance

USE ingestor;

-- Add indexes to the article table for frequently queried columns

-- Index for symbol lookups (used in almost all queries)
CREATE INDEX IF NOT EXISTS idx_article_symbol ON article(symbol);

-- Index for fetched_at (used for date range queries and sorting)
CREATE INDEX IF NOT EXISTS idx_article_fetched_at ON article(fetched_at);

-- Composite index for symbol + fetched_at (most common query pattern)
CREATE INDEX IF NOT EXISTS idx_article_symbol_fetched_at ON article(symbol, fetched_at);

-- Index for price lookups (used in WHERE clauses)
CREATE INDEX IF NOT EXISTS idx_article_price ON article(price);

-- Index for volume_24h (used in WHERE clauses)
CREATE INDEX IF NOT EXISTS idx_article_volume_24h ON article(volume_24h);

-- Composite index for filtering non-null price and volume data
CREATE INDEX IF NOT EXISTS idx_article_price_volume_symbol ON article(price, volume_24h, symbol) 
WHERE price IS NOT NULL AND volume_24h IS NOT NULL;

-- Index for market_cap (used in aggregations and sorting)
CREATE INDEX IF NOT EXISTS idx_article_market_cap ON article(market_cap);

-- Index for url (used in source analysis)
CREATE INDEX IF NOT EXISTS idx_article_url ON article(url(255));

-- Composite index for date-based analytics
CREATE INDEX IF NOT EXISTS idx_article_date_symbol ON article(fetched_at, symbol, price, volume_24h);

-- Show all indexes on the article table
SHOW INDEXES FROM article;

-- Analyze the table to update statistics
ANALYZE TABLE article;

-- Display table statistics
SELECT 
    COUNT(*) as total_rows,
    COUNT(DISTINCT symbol) as unique_symbols,
    COUNT(DISTINCT DATE(fetched_at)) as unique_dates,
    MIN(fetched_at) as earliest_date,
    MAX(fetched_at) as latest_date,
    COUNT(CASE WHEN price IS NOT NULL AND volume_24h IS NOT NULL THEN 1 END) as valid_data_rows
FROM article;

