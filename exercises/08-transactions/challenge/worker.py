"""Processa jobs até não haver mais nenhum pendente.

    uv run python worker.py <nº do worker>

Cada job, numa transação: reclamar (FOR UPDATE SKIP LOCKED), processar (dormir 1 a 5 ms e
inserir uma linha em job_result), marcar como done, COMMIT.
"""

import random
import sys
import time

import psycopg

from db import DATABASE_URL

CLAIM = """
SELECT job_id, payload FROM job
WHERE status = 'pending'
ORDER BY job_id
FOR UPDATE SKIP LOCKED
LIMIT 1
"""

worker = int(sys.argv[1])
done = 0
with psycopg.connect(DATABASE_URL) as conn:
    while True:
        with conn.transaction():
            job = conn.execute(CLAIM).fetchone()
            if job is None:
                break
            job_id, payload = job
            if "sleep" in payload:  # o job lento da tarefa 4
                print(f"worker {worker}: job {job_id} vai demorar {payload['sleep']} s", flush=True)
            time.sleep(payload.get("sleep", random.uniform(0.001, 0.005)))
            conn.execute("INSERT INTO job_result (job_id, worker) VALUES (%s, %s)", (job_id, worker))
            conn.execute("UPDATE job SET status = 'done' WHERE job_id = %s", (job_id,))
        done += 1
print(f"worker {worker}: {done} jobs processados", flush=True)
