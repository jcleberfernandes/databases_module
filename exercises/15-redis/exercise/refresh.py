"""Atualiza a view monthly_revenue, só se ninguém o estiver a fazer (lock no Redis).

    uv run python refresh.py & uv run python refresh.py & wait
"""

import os
import time

import psycopg

from config import DATABASE_URL
from patterns import acquire_lock, release_lock

LOCK = "refresh:monthly_revenue"
pid = os.getpid()

token = acquire_lock(LOCK, seconds=60)  # SET lock:refresh:monthly_revenue <token> NX EX 60
if token is None:
    print(f"[{pid}] lock ocupado: outro processo está a atualizar, saltei")
    raise SystemExit(0)

try:
    print(f"[{pid}] lock obtido (token {token[:8]}...)")
    started = time.perf_counter()
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        conn.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY monthly_revenue")
    print(f"[{pid}] REFRESH feito em {time.perf_counter() - started:.2f} s; a manter o lock 5 s")
    time.sleep(5)  # para a sobreposição com o outro processo ser visível
finally:
    released = release_lock(LOCK, token)
    print(f"[{pid}] lock libertado: {released}")
