"""Insere jobs com payload {"n": <número>}.

    uv run python producer.py              # 10 000 jobs
    uv run python producer.py --slow       # 1 job que demora 30 s a processar (tarefa 4)
"""

import sys

import psycopg
from psycopg.types.json import Jsonb

from db import DATABASE_URL

with psycopg.connect(DATABASE_URL) as conn:
    if "--slow" in sys.argv:
        job_id = conn.execute("INSERT INTO job (payload) VALUES (%s) RETURNING job_id",
                              (Jsonb({"n": 0, "sleep": 30}),)).fetchone()[0]
        print(f"job lento: {job_id}")
    else:
        with conn.cursor() as cur:
            cur.executemany("INSERT INTO job (payload) VALUES (%s)", [(Jsonb({"n": n}),) for n in range(1, 10_001)])
        print("10000 jobs inseridos")
