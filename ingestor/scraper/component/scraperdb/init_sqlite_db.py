import mysql.connector

# conf server local sql
config = {
    "host": "localhost",
    "user": "ingestor_user",
    "password": "password123",
    "database": "ingestor"
}

con = mysql.connector.connect(**config)
cur = con.cursor()

print("Connexion MySQL")

# --- Helper pour créer un index seulement s'il n'existe pas ---
def create_index_if_not_exists(cursor, table: str, index_name: str, index_def: str):
    """
    index_def = "(col1, col2)" par ex.
    """
    cursor.execute(f"SHOW INDEX FROM {table} WHERE Key_name = %s", (index_name,))
    exists = cursor.fetchone()
    if exists:
        print(f"Index {index_name} déjà présent sur {table}, on ne fait rien.")
    else:
        print(f"Création de l'index {index_name} sur {table}...")
        cursor.execute(f"ALTER TABLE {table} ADD INDEX {index_name} {index_def};")


# --- Tables ---
cur.execute('''
CREATE TABLE IF NOT EXISTS symbol (
    id INT PRIMARY KEY AUTO_INCREMENT,
    symbol VARCHAR(255) UNIQUE NOT NULL
);
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS delta (
    id INT PRIMARY KEY AUTO_INCREMENT,
    symbol VARCHAR(255) NOT NULL,
    date_start DATETIME,
    date_end DATE,
    window_label VARCHAR(255),
    delta FLOAT,
    delta_pct FLOAT,
    FOREIGN KEY(symbol) REFERENCES symbol(symbol)
);
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS article (
    id VARCHAR(255) PRIMARY KEY,
    fetched_at DATETIME,
    url TEXT,
    symbol VARCHAR(255) NOT NULL,
    name TEXT,
    price FLOAT,
    market_cap FLOAT,
    volume_24h FLOAT,
    coin_circulating FLOAT,
    FOREIGN KEY(symbol) REFERENCES symbol(symbol)
);
''')


create_index_if_not_exists(
    cur,
    table="article",
    index_name="idx_article_symbol_fetched",
    index_def="(symbol, fetched_at)"
)

create_index_if_not_exists(
    cur,
    table="delta",
    index_name="idx_delta_symbol_dates",
    index_def="(symbol, date_start, date_end)"
)

cur.execute('''
CREATE OR REPLACE VIEW ml_features AS
SELECT
    d.symbol,
    d.date_start,
    d.date_end,
    d.delta_pct AS target_delta_pct,
    CASE WHEN d.delta_pct > 0 THEN 1 ELSE 0 END AS target_up,
    COUNT(a.id)             AS nb_articles,
    AVG(a.price)            AS avg_price,
    AVG(a.market_cap)       AS avg_market_cap,
    AVG(a.coin_circulating) AS avg_circulating,
    AVG(a.volume_24h)       AS avg_volume
FROM delta d
LEFT JOIN article a
  ON a.symbol = d.symbol
 AND a.fetched_at >= d.date_start
 AND a.fetched_at <  d.date_end
GROUP BY
    d.symbol,
    d.date_start,
    d.date_end,
    d.delta_pct;
''')

con.commit()

cur.execute("SHOW TABLES;")
print("Tables dans la DB :", [t[0] for t in cur.fetchall()])

cur.close()
con.close()
print("Init DB terminé ✅")
