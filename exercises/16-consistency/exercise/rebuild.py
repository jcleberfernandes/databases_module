"""Reconstrói customer:{id}:categories para todos os clientes com alugueres.

    uv run python rebuild.py

Uma query ao PostgreSQL e um pipeline ao Redis. Cada set é construído numa chave
temporária e renomeado no fim (RENAME é atómico): quem lê nunca vê um set a meio.
"""

import time

import psycopg
import redis

from config import DATABASE_URL, REDIS_URL

r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# Uma só query: as categorias (sem repetir) de todos os filmes que cada cliente alugou
CATEGORIES_PER_CUSTOMER = """
SELECT r.customer_id, array_agg(DISTINCT c.name ORDER BY c.name) AS categories
FROM rental r
JOIN inventory i      USING (inventory_id)
JOIN film_category fc USING (film_id)
JOIN category c       USING (category_id)
GROUP BY r.customer_id
ORDER BY r.customer_id
"""
PATTERN = "customer:*:categories"

started = time.perf_counter()

with psycopg.connect(DATABASE_URL) as conn:
    rows = conn.execute(CATEGORIES_PER_CUSTOMER).fetchall()           # a única query
expected = {customer_id for customer_id, _ in rows}

# Chaves que existem mas não deviam (cliente sem alugueres, ou que já não existe)
stale = [k for k in r.scan_iter(match=PATTERN, count=1000) if int(k.split(":")[1]) not in expected]

with r.pipeline(transaction=False) as pipe:                           # o único pipeline
    for customer_id, categories in rows:
        key = f"customer:{customer_id}:categories"
        tmp = f"tmp:{key}"
        pipe.delete(tmp)
        pipe.sadd(tmp, *categories)
        pipe.rename(tmp, key)    # substitui o set antigo de uma vez
    for k in stale:
        pipe.delete(k)
    pipe.execute()

print(f"rebuild: {len(rows)} sets escritos, {len(stale)} chaves a mais apagadas, "
      f"1 query + 1 pipeline, {time.perf_counter() - started:.2f} s")
count = sum(1 for _ in r.scan_iter(match=PATTERN, count=1000))
print(f"SCAN {PATTERN}: {count} chaves")
