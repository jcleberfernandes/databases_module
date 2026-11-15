"""Exercício 15: quatro padrões Redis sobre o Pagila."""

import json
import time
import uuid
from decimal import Decimal

import psycopg
import redis

from config import DATABASE_URL, REDIS_URL

r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# ---------------------------------------------------------------- 1. filmes vistos recentemente
VIEWED_MAX = 20
VIEWED_TTL = 30 * 24 * 3600  # 30 dias = 2 592 000 s


def record_view(customer_id: int, film_id: int) -> None:
    key = f"customer:{customer_id}:viewed"
    with r.pipeline() as pipe:  # MULTI/EXEC: os três comandos juntos
        pipe.zadd(key, {film_id: time.time()})         # o mesmo filme só atualiza o score (sem duplicar)
        pipe.zremrangebyrank(key, 0, -(VIEWED_MAX + 1))  # fica só com os 20 mais recentes
        pipe.expire(key, VIEWED_TTL)                     # expira 30 dias depois da última visita
        pipe.execute()


def recent_views(customer_id: int) -> list[int]:
    return [int(f) for f in r.zrange(f"customer:{customer_id}:viewed", 0, -1, desc=True)]


# ---------------------------------------------------------------- 2. cache-aside
FILM_TTL = 300


def get_film(film_id: int) -> tuple[dict, bool]:
    """Devolve (filme, hit). hit=True se veio do Redis."""
    key = f"cache:film:{film_id}"
    cached = r.get(key)
    if cached is not None:
        return json.loads(cached), True
    with psycopg.connect(DATABASE_URL) as conn:
        title, rating, length, rate = conn.execute(
            "SELECT title, rating::text, length, rental_rate FROM film WHERE film_id = %s", (film_id,)
        ).fetchone()
    film = {"title": title, "rating": rating, "length": length, "rental_rate": str(rate)}
    r.set(key, json.dumps(film), ex=FILM_TTL)
    return film, False


def update_film_rate(film_id: int, rate: Decimal) -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute("UPDATE film SET rental_rate = %s WHERE film_id = %s", (rate, film_id))
    # Só depois do COMMIT: apagar a cópia; a próxima leitura vai ao PostgreSQL
    r.delete(f"cache:film:{film_id}")


# ---------------------------------------------------------------- 3. lock
# Apaga a chave só se ainda tiver o NOSSO token (GET e DEL juntos, de forma atómica)
_release = r.register_script("""
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
end
return 0
""")


def acquire_lock(name: str, seconds: int = 60) -> str | None:
    """Devolve o token se conseguiu o lock, None se outro o tem."""
    token = str(uuid.uuid4())
    return token if r.set(f"lock:{name}", token, nx=True, ex=seconds) else None


def release_lock(name: str, token: str) -> bool:
    return _release(keys=[f"lock:{name}"], args=[token]) == 1


# ---------------------------------------------------------------- 4. rate limit (janela fixa)
RATE_LIMIT = 10


def allow_request(customer_id: int) -> bool:
    window = int(time.time() // 60)                     # nº do minuto atual
    key = f"ratelimit:customer:{customer_id}:{window}"
    with r.pipeline() as pipe:
        pipe.incr(key)
        pipe.expire(key, 60)                            # o contador desaparece depois do minuto
        count, _ = pipe.execute()
    return count <= RATE_LIMIT
