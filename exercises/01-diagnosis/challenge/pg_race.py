"""10 processos, cada um com a sua ligação, inserem 1 000 registos cada na tabela record,
um INSERT por registo.

    uv run python pg_race.py
"""

import os
from multiprocessing import Pool
from pathlib import Path

import psycopg
from dotenv import dotenv_values, load_dotenv

load_dotenv()
_root = dotenv_values(Path(__file__).resolve().parents[3] / ".env")
DATABASE_URL = os.environ.get("DATABASE_URL") or (
    f"postgresql://{_root['POSTGRES_USER']}:{_root['POSTGRES_PASSWORD']}@localhost:5432/ch01"
)
WORKERS = 10
RECORDS = 1_000


def insert_records(worker: int) -> None:
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        for n in range(RECORDS):
            conn.execute("INSERT INTO record (worker, n) VALUES (%s, %s)", (worker, n))


if __name__ == "__main__":
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS record (worker integer NOT NULL, n integer NOT NULL)")
        conn.execute("TRUNCATE record")  # começar vazia
    with Pool(WORKERS) as pool:
        pool.map(insert_records, range(WORKERS))
    with psycopg.connect(DATABASE_URL) as conn:
        count = conn.execute("SELECT count(*) FROM record").fetchone()[0]
    print(f"PostgreSQL: SELECT count(*) FROM record = {count}")
