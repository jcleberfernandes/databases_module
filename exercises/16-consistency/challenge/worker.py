"""Lê a outbox e acrescenta as categorias de cada filme a customer:{customer_id}:categories.

    uv run python worker.py

Cada lote, numa transação do PostgreSQL:
  1. reclama até 50 linhas por processar (FOR UPDATE SKIP LOCKED)
  2. SADD das categorias no Redis
  3. processed_at = now() e COMMIT
Se o worker morrer, ou o Redis falhar, antes do COMMIT, as linhas voltam a ficar livres
e são processadas outra vez (SADD repetido não faz mal).
"""

import os
import sys
import time
from pathlib import Path

import psycopg
import redis

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "exercise"))
from config import DATABASE_URL, REDIS_URL  # noqa: E402

BATCH = 50
PAUSE = 0.3  # entre o Redis e o COMMIT, para ser possível matar o worker "a meio de um lote"

CLAIM = """
SELECT o.outbox_id, o.customer_id, o.film_id
FROM outbox o
WHERE o.processed_at IS NULL
ORDER BY o.outbox_id
LIMIT %s
FOR UPDATE SKIP LOCKED
"""
FILM_CATEGORIES = """
SELECT fc.film_id, array_agg(c.name) FROM film_category fc JOIN category c USING (category_id)
WHERE fc.film_id = ANY(%s) GROUP BY fc.film_id
"""


def log(msg):
    print(f"{time.strftime('%H:%M:%S')} [worker {os.getpid()}] {msg}", flush=True)


r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
log("arrancou")

with psycopg.connect(DATABASE_URL) as conn:
    while True:
        try:
            # Só escreve no Redis com fsync a cada escrita (ver README); depois de um reinício espera
            if r.config_get("appendfsync")["appendfsync"] != "always":
                log("Redis sem appendfsync always: à espera")
                time.sleep(1)
                continue
            with conn.transaction():
                rows = conn.execute(CLAIM, (BATCH,)).fetchall()
                if not rows:
                    time.sleep(0.5)
                    continue
                categories = dict(conn.execute(FILM_CATEGORIES, ([f for _, _, f in rows],)).fetchall())
                with r.pipeline(transaction=False) as pipe:
                    for _, customer_id, film_id in rows:
                        if categories.get(film_id):
                            pipe.sadd(f"customer:{customer_id}:categories", *categories[film_id])
                    pipe.execute()
                log(f"lote {rows[0][0]}..{rows[-1][0]} ({len(rows)} linhas): Redis escrito, a fazer COMMIT")
                time.sleep(PAUSE)
                conn.execute("UPDATE outbox SET processed_at = now() WHERE outbox_id = ANY(%s)",
                             ([o for o, _, _ in rows],))
            log(f"lote {rows[0][0]}..{rows[-1][0]}: COMMIT")
        except redis.RedisError as e:
            # A transação do PostgreSQL já foi desfeita (saímos do with com erro): o lote fica por processar
            log(f"erro no Redis ({type(e).__name__}): ROLLBACK, tento outra vez daqui a 1 s")
            time.sleep(1)
