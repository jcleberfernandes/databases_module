"""Write skew. Regra: cada loja tem pelo menos um funcionário ativo.
20 threads, uma por funcionário ativo da loja 1, cada uma com a sua ligação.
Cada uma conta os ativos da loja 1 e, se forem mais de 1, desativa o seu funcionário.

    uv run python write_skew.py read_committed
    uv run python write_skew.py serializable
"""

import os
import sys
import threading
from pathlib import Path

import psycopg
from dotenv import dotenv_values, load_dotenv
from psycopg import errors

load_dotenv()
_root = dotenv_values(Path(__file__).resolve().parents[3] / ".env")
DATABASE_URL = os.environ.get("DATABASE_URL") or (
    f"postgresql://{_root['POSTGRES_USER']}:{_root['POSTGRES_PASSWORD']}@localhost:5432/ex08"
)
LEVEL = {"read_committed": "READ COMMITTED", "serializable": "SERIALIZABLE"}[sys.argv[1]]

with psycopg.connect(DATABASE_URL) as conn:
    staff = [r[0] for r in conn.execute("SELECT staff_id FROM staff WHERE store_id = 1 AND active ORDER BY 1")]
print(f"{LEVEL}: {len(staff)} funcionários ativos na loja 1 no início")

barrier = threading.Barrier(len(staff))  # todos leem antes de algum escrever
retries = 0
lock = threading.Lock()


def deactivate(staff_id: int) -> None:
    global retries
    first_try = True
    with psycopg.connect(DATABASE_URL) as conn:
        while True:
            try:
                with conn.transaction():
                    conn.execute(f"SET TRANSACTION ISOLATION LEVEL {LEVEL}")
                    active = conn.execute(
                        "SELECT count(*) FROM staff WHERE store_id = 1 AND active"
                    ).fetchone()[0]
                    if first_try:
                        barrier.wait()  # só na 1.ª tentativa, não nas repetições
                    if active > 1:
                        conn.execute("UPDATE staff SET active = false WHERE staff_id = %s", (staff_id,))
                return
            except errors.SerializationFailure:  # SQLSTATE 40001: repetir a transação desde o início
                first_try = False
                with lock:
                    retries += 1


threads = [threading.Thread(target=deactivate, args=(s,)) for s in staff]
for t in threads:
    t.start()
for t in threads:
    t.join()

with psycopg.connect(DATABASE_URL) as conn:
    active = conn.execute("SELECT count(*) FROM staff WHERE store_id = 1 AND active").fetchone()[0]
print(f"{LEVEL}: {active} funcionários ativos na loja 1 no fim ({retries} transações repetidas)")
