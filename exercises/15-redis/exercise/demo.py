"""Demonstração dos padrões 1, 2 e 4 (o 3, o lock, está em refresh.py).

    uv run python demo.py
"""

import time
from decimal import Decimal

from patterns import (allow_request, get_film, r, recent_views, record_view, update_film_rate)

# Começar limpo (só as chaves desta demonstração)
r.delete("customer:1:viewed", "cache:film:1")
for key in r.scan_iter("ratelimit:customer:1:*"):
    r.delete(key)

print("=== 1. Filmes vistos recentemente")
for film_id in range(1, 26):
    record_view(1, film_id)
print("cliente 1 viu os filmes 1 a 25 por ordem")
print("recent_views(1) =", recent_views(1))
record_view(1, 10)
print("viu o filme 10 outra vez")
print("recent_views(1) =", recent_views(1), f"({len(recent_views(1))} filmes, sem duplicados)")
print("TTL customer:1:viewed =", r.ttl("customer:1:viewed"), "s")

print("\n=== 2. Cache-aside (filme 1)")
film, hit = get_film(1)
print(f"get_film(1) -> {'HIT' if hit else 'MISS'} {film}")
film, hit = get_film(1)
print(f"get_film(1) -> {'HIT' if hit else 'MISS'} {film}  (TTL {r.ttl('cache:film:1')} s)")
update_film_rate(1, Decimal("1.99"))
print("update_film_rate(1, 1.99) -> PostgreSQL atualizado, cache:film:1 apagada:", not r.exists("cache:film:1"))
film, hit = get_film(1)
print(f"get_film(1) -> {'HIT' if hit else 'MISS'} {film}")

print("\n=== 4. Rate limit (10 pedidos por minuto)")
# Esperar pelo início de um minuto, para os 12 pedidos caberem todos no mesmo minuto
time.sleep(60 - time.time() % 60 + 0.1)
results = [allow_request(1) for _ in range(12)]
print(f"{time.strftime('%H:%M:%S')} 12 pedidos seguidos ->", results)
print(f"True: {results.count(True)}  False: {results.count(False)}")
time.sleep(60 - time.time() % 60 + 0.1)
print(f"{time.strftime('%H:%M:%S')} minuto seguinte -> allow_request(1) =", allow_request(1))
