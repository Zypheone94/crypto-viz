import duckdb
from pathlib import Path

PARQUET_PATH = Path(__file__).parent.parent.parent.parent / "data" / "clean" / "parquet"

db = duckdb.connect(Path(__file__).parent.parent.parent / "data" / "duck" / "warehouse.duckdb")

for filename in PARQUET_PATH.glob("*.parquet"):
    table = filename.stem

    db.execute(f"INSERT INTO {table} SELECT * FROM read_parquet('{filename}')")