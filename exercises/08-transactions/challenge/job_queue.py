"""Fila de jobs em PostgreSQL com SELECT ... FOR UPDATE SKIP LOCKED.

    uv run python job_queue.py ex08 run    # cria a tabela, 10 000 jobs, 8 workers, verifica
    uv run python job_queue.py ex08 kill   # mata um worker a meio de um job
"""

import multiprocessing
import os
import signal
import sys
import time

from db import connect

SETUP = """
DROP TABLE IF EXISTS job_log, job;
CREATE TABLE job (
    id      int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    payload text NOT NULL,
    status  text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'done')),
    done_by int
);
-- Cada vez que um job é processado fica aqui uma linha: serve para provar "exatamente uma vez"
CREATE TABLE job_log (job_id int NOT NULL REFERENCES job, worker int NOT NULL);
"""

CLAIM = """
SELECT id, payload FROM job
WHERE status = 'pending'
ORDER BY id
FOR UPDATE SKIP LOCKED
LIMIT 1
"""


def producer(n):
    with connect() as conn:
        with conn.cursor() as cur:
            cur.executemany("INSERT INTO job (payload) VALUES (%s)", [(f"job {i}",) for i in range(n)])
    print(f"produtor: {n} jobs inseridos")


def worker(seconds_per_job=0.0):
    pid = os.getpid()
    done = 0
    with connect() as conn:
        while True:
            # Reclamar, processar e marcar como feito na MESMA transação:
            # se o worker morrer a meio, o PostgreSQL faz rollback e o job volta a estar livre.
            with conn.transaction():
                job = conn.execute(CLAIM).fetchone()
                if job is None:
                    break
                time.sleep(seconds_per_job)  # "processar" o job
                conn.execute("INSERT INTO job_log (job_id, worker) VALUES (%s, %s)", (job[0], pid))
                conn.execute("UPDATE job SET status = 'done', done_by = %s WHERE id = %s", (pid, job[0]))
            done += 1
    print(f"worker {pid}: {done} jobs")


def check():
    with connect() as conn:
        row = conn.execute("""
            SELECT (SELECT count(*) FROM job)                               AS jobs,
                   (SELECT count(*) FROM job WHERE status = 'done')         AS done,
                   (SELECT count(*) FROM job_log)                           AS processed,
                   (SELECT count(DISTINCT job_id) FROM job_log)             AS distinct_jobs,
                   (SELECT count(*) FROM (SELECT job_id FROM job_log GROUP BY job_id
                                          HAVING count(*) > 1) d)           AS processed_twice
        """).fetchone()
    print(f"jobs={row[0]} done={row[1]} processados={row[2]} jobs_distintos={row[3]} repetidos={row[4]}")
    ok = row[0] == row[1] == row[2] == row[3] and row[4] == 0
    print("cada job foi processado exatamente uma vez" if ok else "ERRO: há jobs perdidos ou repetidos")


def run():
    with connect() as conn:
        conn.execute(SETUP)
    producer(10_000)
    started = time.perf_counter()
    workers = [multiprocessing.Process(target=worker) for _ in range(8)]
    for w in workers:
        w.start()
    for w in workers:
        w.join()
    print(f"8 workers terminaram em {time.perf_counter() - started:.1f} s")
    check()


def job_state(job_id):
    with connect() as conn:
        status = conn.execute("SELECT status, done_by FROM job WHERE id = %s", (job_id,)).fetchone()
        # Se outro worker conseguir reclamá-lo agora, o job está livre
        free = conn.execute(CLAIM.replace("WHERE status", f"WHERE id = {job_id} AND status")).fetchone()
        log = conn.execute("SELECT worker FROM job_log WHERE job_id = %s", (job_id,)).fetchall()
    return f"status={status[0]} done_by={status[1]} livre_para_outro_worker={free is not None} job_log={log}"


def kill():
    with connect() as conn:
        job_id = conn.execute("INSERT INTO job (payload) VALUES ('job lento') RETURNING id").fetchone()[0]
    print(f"novo job {job_id}")

    slow = multiprocessing.Process(target=worker, args=(60,))  # demora 60 s por job
    slow.start()
    time.sleep(1)
    print(f"worker {slow.pid} a meio do job:   {job_state(job_id)}")

    os.kill(slow.pid, signal.SIGKILL)  # morte súbita: sem COMMIT nem ROLLBACK
    slow.join()
    time.sleep(1)  # o servidor percebe que a ligação caiu e faz rollback
    print(f"worker {slow.pid} morto (SIGKILL): {job_state(job_id)}")

    other = multiprocessing.Process(target=worker)
    other.start()
    other.join()
    print(f"depois de outro worker:      {job_state(job_id)}")
    check()


if __name__ == "__main__":
    {"run": run, "kill": kill}[sys.argv[2]]()
