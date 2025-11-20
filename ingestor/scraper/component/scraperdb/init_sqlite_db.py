import mysql.connector

#conf server local sql
config = {
    "host": "localhost",
    "user": "ingestor_user",
    "password": "password123",
    "database": "ingestor"
}

con = mysql.connector.connect(**config)
cur = con.cursor()

print("Connexion MySQL")

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

con.commit()

cur.execute("SHOW TABLES;")
print("Tables dans la DB :", [t[0] for t in cur.fetchall()])

cur.close()
con.close()
