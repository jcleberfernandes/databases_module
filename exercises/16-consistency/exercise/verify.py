"""Compara cada customer:{id}:categories com o PostgreSQL (tamanho e membros).
Também avisa de chaves para clientes que não deviam ter uma.
Sai com 0 se estiver tudo igual, 1 se houver diferenças.

    uv run python verify.py
"""

import sys

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


with psycopg.connect(DATABASE_URL) as conn:
    expected = {customer_id: set(categories) for customer_id, categories in conn.execute(CATEGORIES_PER_CUSTOMER)}

ids = sorted(expected)
with r.pipeline(transaction=False) as pipe:
    for customer_id in ids:
        pipe.smembers(f"customer:{customer_id}:categories")
    in_redis = dict(zip(ids, pipe.execute()))

differences = 0
for customer_id in ids:
    want, have = expected[customer_id], in_redis[customer_id]
    if want != have:
        differences += 1
        print(f"customer:{customer_id}:categories: PostgreSQL {len(want)}, Redis {len(have)}"
              f" | em falta no Redis: {sorted(want - have)} | a mais no Redis: {sorted(have - want)}")

for k in r.scan_iter(match=PATTERN, count=1000):
    if int(k.split(":")[1]) not in expected:
        differences += 1
        print(f"{k}: não devia existir (o cliente não tem alugueres) | membros: {sorted(r.smembers(k))}")

print(f"verify: {len(ids)} sets comparados, {differences} diferenças")
sys.exit(1 if differences else 0)
