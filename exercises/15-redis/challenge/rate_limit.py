"""Rate limit de 10 pedidos por 60 s: janela fixa e janela deslizante.
As duas funções recebem a hora (now, em segundos) para os testes controlarem o relógio."""

import os
import uuid
from pathlib import Path

import redis
from dotenv import dotenv_values, load_dotenv

load_dotenv()
_root = dotenv_values(Path(__file__).resolve().parents[3] / ".env")
REDIS_URL = os.environ.get("REDIS_URL") or f"redis://:{_root['REDIS_PASSWORD']}@localhost:6379/0"

LIMIT = 10
WINDOW = 60

r = redis.Redis.from_url(REDIS_URL, decode_responses=True)


def allow_request_fixed(customer_id: int, now: float) -> bool:
    """Janela fixa: um contador por minuto do relógio (como no exercício)."""
    key = f"ratelimit:fixed:{customer_id}:{int(now // WINDOW)}"
    with r.pipeline() as pipe:
        pipe.incr(key)
        pipe.expire(key, WINDOW)
        count, _ = pipe.execute()
    return count <= LIMIT


# Tudo num só passo atómico: o Redis corre o script inteiro sem nenhum outro comando pelo meio.
_sliding = r.register_script("""
local key, now, window, limit, member = KEYS[1], tonumber(ARGV[1]), tonumber(ARGV[2]), tonumber(ARGV[3]), ARGV[4]
redis.call('ZREMRANGEBYSCORE', key, '-inf', now - window)   -- tira os pedidos com mais de 60 s
if redis.call('ZCARD', key) < limit then                     -- conta os que ficam
    redis.call('ZADD', key, now, member)                     -- e regista este
    redis.call('EXPIRE', key, window)
    return 1
end
return 0
""")


def allow_request_sliding(customer_id: int, now: float) -> bool:
    """Janela deslizante: no máximo 10 pedidos em quaisquer 60 s.
    Sorted set com score = hora do pedido; o membro tem um uuid para ser único
    mesmo quando dois pedidos têm exatamente a mesma hora."""
    member = f"{now}:{uuid.uuid4()}"
    return _sliding(keys=[f"ratelimit:sliding:{customer_id}"], args=[now, WINDOW, LIMIT, member]) == 1
