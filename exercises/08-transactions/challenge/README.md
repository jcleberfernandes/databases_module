# Challenge 08 — Fila de jobs em PostgreSQL

Ficheiros: `producer.py`, `worker.py`, `db.py`, `setup.sql` (as tabelas do enunciado),
`check.sql` (as queries da prova), `pyproject.toml`, `.env.example`.

## Como correr

```bash
./scripts/create-db.sh ch08 --reset
docker compose exec -T postgres psql -U postgres -d ch08 -v ON_ERROR_STOP=1 < exercises/08-transactions/challenge/setup.sql
cd exercises/08-transactions/challenge
uv run python producer.py                                   # 10 000 jobs {"n": 1..10000}
for w in 1 2 3 4 5 6 7 8; do uv run python worker.py $w & done; wait    # 8 workers ao mesmo tempo
cd ../../..
docker compose exec -T postgres psql -U postgres -d ch08 < exercises/08-transactions/challenge/check.sql
```

Cada worker repete até não haver jobs pendentes. Numa transação:

```sql
SELECT job_id, payload FROM job WHERE status = 'pending' ORDER BY job_id FOR UPDATE SKIP LOCKED LIMIT 1;
-- dorme 1 a 5 ms
INSERT INTO job_result (job_id, worker) VALUES (...);
UPDATE job SET status = 'done' WHERE job_id = ...;
COMMIT;
```

## Tarefa 3 — cada job processado exatamente uma vez

```
worker 1: 1263 jobs processados
worker 8: 1220 jobs processados
worker 3: 1259 jobs processados
worker 4: 1219 jobs processados
worker 7: 1257 jobs processados
worker 6: 1258 jobs processados
worker 2: 1257 jobs processados
worker 5: 1267 jobs processados
real	0m15.593s
```

`check.sql`:

```
 jobs  | done  | results | distinct_jobs
-------+-------+---------+---------------
 10000 | 10000 |   10000 |         10000

-- jobs com mais de uma linha em job_result
 job_id | count
--------+-------
(0 rows)
```

10 000 linhas em `job_result` e nenhum `job_id` repetido. O `FOR UPDATE` bloqueia o job reclamado
e o `SKIP LOCKED` faz os outros workers saltarem os jobs bloqueados em vez de esperarem: cada job
só é apanhado por um worker, e os 8 trabalham ao mesmo tempo (~1 250 jobs cada).

## Tarefa 4 — matar o worker a meio de um job

```bash
uv run python producer.py --slow     # job 10001 com {"n": 0, "sleep": 30}: o worker dorme 30 s
uv run python worker.py 9 &          # apanha o job 10001
kill -9 <pid do worker 9>            # enquanto dorme
uv run python worker.py 10
```

Durante o sono do worker 9:

```
 job_id | status  | results | by_worker
--------+---------+---------+-----------
  10001 | pending |       0 |

 pid  |        state        |           last_query
------+---------------------+---------------------------------
 5917 | idle in transaction | SELECT job_id, payload FROM job WHERE status = 'pending' ...

 claimable          (outra sessão: SELECT ... FOR UPDATE SKIP LOCKED LIMIT 1)
-----------
(0 rows)
```

O job ainda está `pending` e sem resultado, mas a transação do worker 9 tem o **lock da linha**:
outra sessão não o consegue reclamar (o `SKIP LOCKED` salta-o e não encontra mais nada).

Depois do `kill -9`:

```
 job_id | status  | results | by_worker
--------+---------+---------+-----------
  10001 | pending |       0 |

 pid | state | last_query
-----+-------+------------
(0 rows)

 claimable
-----------
     10001
```

A ligação caiu e o PostgreSQL fez **rollback** da transação do worker 9: o lock desapareceu, o job
continua `pending` e não ficou nenhuma linha em `job_result` (o `INSERT` nem chegou a ser feito, e
seria desfeito na mesma). O job está livre outra vez.

O worker 10 apanha-o:

```
worker 10: job 10001 vai demorar 30 s
worker 10: 1 jobs processados

 job_id | status | results | by_worker
--------+--------+---------+-----------
  10001 | done   |       1 | 10
```

**E se o processamento enviasse um email em vez de inserir uma linha?** O `INSERT` em
`job_result` está dentro da transação, por isso é desfeito com ela: nunca fica feito "a meio". Um
email não se desfaz. Se o worker enviasse o email e morresse antes do `COMMIT`, o job voltava a
`pending` e outro worker enviava o email **outra vez**: o cliente recebia dois. A fila garante
"pelo menos uma vez", não "exatamente uma vez", para efeitos fora da base de dados. Para evitar
repetidos é preciso guardar uma marca de "email já enviado" (por exemplo uma chave de idempotência
que o serviço de email aceite), ou registar o envio numa tabela e só enviar a partir dela.
