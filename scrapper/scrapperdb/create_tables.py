import duckdb

# Create or connect to the database
conn = duckdb.connect('cryptodb.duckdb')

# Create the table
conn.execute('''
CREATE SEQUENCE IF NOT EXISTS seq_scraps_id START 1;
CREATE TABLE IF NOT EXISTS Scraps (
    id INTEGER PRIMARY KEY DEFAULT nextval('seq_scraps_id'),
    heure DATE,
    path TEXT,
    text TEXT
);
''')

conn.close()
print("Done — 'cryptodb.db' created (table Scraps).")