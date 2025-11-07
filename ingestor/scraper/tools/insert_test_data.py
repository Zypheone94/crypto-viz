"""Script pour insérer des données de test dans la base SQLite."""
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import sys

# Ajouter le chemin parent pour importer le module
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scraper.api.utils.sqlite_client import get_db_path

def insert_test_data():
    db_path = get_db_path()
    print(f"Insertion des données de test dans {db_path}")
    
    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    
    # Insérer des symboles
    symbols = [
        ('BTC',),
        ('ETH',),
        ('SOL',),
        ('ADA',),
        ('DOT',)
    ]
    cur.executemany("INSERT OR IGNORE INTO symbol (symbol) VALUES (?)", symbols)
    
    # Insérer des articles avec des dates variées
    base_date = datetime.now() - timedelta(days=7)
    articles = []
    
    for i in range(50):
        date = base_date + timedelta(hours=i*3)
        symbol = ['BTC', 'ETH', 'SOL', 'ADA', 'DOT'][i % 5]
        source = ['coindesk', 'cointelegraph', 'decrypt', 'theblock'][i % 4]
        price = 50000 + (i * 100) if symbol == 'BTC' else 3000 + (i * 10)
        
        articles.append((
            date.strftime('%Y-%m-%d %H:%M:%S'),
            f'Article {i}: {symbol} price update',
            f'https://example.com/article-{i}',
            source,
            symbol,
            f'{symbol} Coin',
            price,
            price * 19000000,  # market_cap
            19000000  # coin_circulating
        ))
    
    cur.executemany("""
        INSERT INTO article (date, titre, url, source, symbol, name, price, market_cap, coin_circulating)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, articles)
    
    # Insérer des deltas
    deltas = []
    for i in range(20):
        date_start = base_date + timedelta(hours=i*6)
        date_end = date_start + timedelta(hours=1)
        symbol = ['BTC', 'ETH', 'SOL'][i % 3]
        delta = (i % 10 - 5) * 100  # Variations entre -500 et 500
        delta_pct = (i % 10 - 5) * 0.5  # Variations entre -2.5% et 2.5%
        
        deltas.append((
            symbol,
            date_start.strftime('%Y-%m-%d %H:%M:%S'),
            date_end.strftime('%Y-%m-%d'),
            '1h',
            delta,
            delta_pct
        ))
    
    cur.executemany("""
        INSERT INTO delta (symbol, date_start, date_end, window_label, delta, delta_pct)
        VALUES (?, ?, ?, ?, ?, ?)
    """, deltas)
    
    con.commit()
    
    # Afficher les statistiques
    print("\n📊 Statistiques:")
    print(f"  - Symboles: {cur.execute('SELECT COUNT(*) FROM symbol').fetchone()[0]}")
    print(f"  - Articles: {cur.execute('SELECT COUNT(*) FROM article').fetchone()[0]}")
    print(f"  - Deltas: {cur.execute('SELECT COUNT(*) FROM delta').fetchone()[0]}")
    
    # Afficher quelques exemples
    print("\n📰 Exemples d'articles:")
    for row in cur.execute("SELECT date, source, symbol, price FROM article LIMIT 5").fetchall():
        print(f"  - {row[0]} | {row[1]:15} | {row[2]:4} | ${row[3]:,.2f}")
    
    print("\n📈 Exemples de deltas:")
    for row in cur.execute("SELECT symbol, date_start, delta_pct FROM delta LIMIT 5").fetchall():
        print(f"  - {row[0]:4} | {row[1]} | {row[2]:+.2f}%")
    
    con.close()
    print("\n✅ Données de test insérées avec succès!")

if __name__ == "__main__":
    insert_test_data()
