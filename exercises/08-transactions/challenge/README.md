# Challenge 08 — Fila de jobs em PostgreSQL

Ficheiros: `job_queue.py`, `db.py`, `pyproject.toml`.

```bash
cd exercises/08-transactions/challenge
uv run python job_queue.py ex08 run    # tabela job, produtor de 10 000 jobs, 8 workers, verificação
uv run python job_queue.py ex08 kill   # mata um worker a meio de um job
```

Cada worker (processo separado, `multiprocessing`) repete numa transação:

```sql
SELECT id, payload FROM job WHERE status = 'pending' ORDER BY id
FOR UPDATE SKIP LOCKED LIMIT 1;
-- processa
INSERT INTO job_log (job_id, worker) VALUES (...);
UPDATE job SET status = 'done', done_by = ... WHERE id = ...;
COMMIT;
```

`FOR UPDATE` bloqueia o job; `SKIP LOCKED` faz os outros workers saltarem os
jobs bloqueados em vez de esperarem, por isso os 8 trabalham em paralelo sem
pegar no mesmo job.

## Prova: cada job processado exatamente uma vez

`job_log` guarda uma linha por cada vez que um job é processado.

```
produtor: 10000 jobs inseridos
worker 27493: 1249 jobs
worker 27496: 1245 jobs
worker 27501: 1245 jobs
worker 27495: 1258 jobs
worker 27504: 1240 jobs
worker 27494: 1256 jobs
worker 27503: 1255 jobs
worker 27498: 1252 jobs
8 workers terminaram em 12.9 s
jobs=10000 done=10000 processados=10000 jobs_distintos=10000 repetidos=0
cada job foi processado exatamente uma vez
```

## Matar um worker a meio de um job

Um worker lento (60 s por job) pega num job novo e é morto com `SIGKILL`:

```
novo job 10001
worker 27805 a meio do job:   status=pending done_by=None livre_para_outro_worker=False job_log=[]
worker 27805 morto (SIGKILL): status=pending done_by=None livre_para_outro_worker=True job_log=[]
worker 27817: 1 jobs
depois de outro worker:      status=done done_by=27817 livre_para_outro_worker=False job_log=[(27817,)]
jobs=10001 done=10001 processados=10001 jobs_distintos=10001 repetidos=0
cada job foi processado exatamente uma vez
```

O que acontece: enquanto o worker está vivo, o job está bloqueado e mais
ninguém lhe pega. Quando o processo morre, a ligação cai e o PostgreSQL faz
**rollback** da transação: o lock desaparece e o job continua `pending` (o
`INSERT` em `job_log` também foi desfeito). O próximo worker pega nele e
processa-o. O job não se perde nem é feito duas vezes.

Atenção: isto só é verdade porque o "processamento" está dentro da transação.
Se o job fizesse algo fora da base de dados (ex: enviar um email), esse efeito
podia acontecer duas vezes.
