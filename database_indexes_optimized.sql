USE ingestor;

CREATE INDEX idx_article_symbol_fetched ON article(symbol, fetched_at DESC);
CREATE INDEX idx_article_fetched_desc ON article(fetched_at DESC);
CREATE INDEX idx_article_valid_data ON article(fetched_at DESC, symbol, price, volume_24h, market_cap, name)
WHERE price IS NOT NULL AND volume_24h IS NOT NULL;
CREATE INDEX idx_article_market_cap ON article(market_cap DESC, fetched_at DESC)
WHERE market_cap IS NOT NULL;
CREATE INDEX idx_article_symbol ON article(symbol);
CREATE INDEX idx_article_url ON article(url(191));

CREATE INDEX idx_delta_window_symbol_date ON delta(window_label, symbol, date_end DESC);
CREATE INDEX idx_delta_window_pct ON delta(window_label, delta_pct DESC, date_end DESC);
CREATE INDEX idx_delta_symbol_date ON delta(symbol, date_end DESC);

ANALYZE TABLE article;
ANALYZE TABLE delta;

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

