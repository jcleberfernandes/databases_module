# Challenge 09 — A mesma API, com utilizadores de privilégios diferentes

Ficheiros:
- `api/main.py`, `api/pyproject.toml` — a API do exercício com 3 `GET` novos e o tratamento dos `403`.
- `.env.a.example` (instância A) e `.env.b.example` (instância B).
- `users.sh` — cria os utilizadores só de leitura do MongoDB e do Redis.
- `.gitignore` — impede o commit de `.env.a` e `.env.b`.

## Utilizadores

| Motor | Instância A (exercício) | Instância B (só leitura) |
|---|---|---|
| PostgreSQL | `ex09_app` | `ex09_readonly` (já existe, do exercício) |
| MongoDB | `ex09_app` (`readWrite` em `ex09`) | `ex09_reader` (`read` em `ex09`) |
| Redis | `ex09_app` (`INCR` e `GET` em `counter:*`) | `ex09_reader` (só `GET` em `counter:*`) |

O `users.sh` também junta `+get` ao `ex09_app` do Redis: no exercício ele só podia fazer `INCR`, e
sem `GET` a leitura do contador falhava na instância A.

## Como correr

```bash
# depois do exercício (base ex09, users.sh do exercício)
cd exercises/09-security/challenge
cp .env.a.example .env.a      # as passwords do .env do exercício
cp .env.b.example .env.b      # a do ex09_readonly do exercício e duas novas
cd ../../.. && bash exercises/09-security/challenge/users.sh
cd exercises/09-security/challenge/api
uv run --env-file ../.env.a uvicorn main:app --port 8001 &     # instância A
uv run --env-file ../.env.b uvicorn main:app --port 8002 &     # instância B
```

As duas instâncias correm **o mesmo código**; só o ficheiro de variáveis de ambiente muda.

## Como aparecem os `403`

Três exception handlers convertem os erros de privilégio de cada motor em `403`:

| Motor | Erro | Resposta |
|---|---|---|
| PostgreSQL | `psycopg.errors.InsufficientPrivilege` (SQLSTATE `42501`) | 403 |
| MongoDB | `OperationFailure` com `code == 13` (`Unauthorized`) | 403 |
| Redis | `redis.exceptions.NoPermissionError` (`NOPERM`) | 403 |

Qualquer outro erro continua a dar `500`. O código não verifica em que instância está: quem
recusa a escrita é a base de dados.

## Tarefa 5 — pedidos e respostas

```
############ instância A (porta 8001)
$ curl -X POST localhost:8001/actors -H Content-Type:application/json -d {"first_name": "GRACE", "last_name": "HOPPER"}
{"actor_id":204}  -> HTTP 201
$ curl -X POST localhost:8001/notes -H Content-Type:application/json -d {"customer_id": 1, "text": "nota da porta 8001"}
{"_id":"6aec6e0af6d05c328f8888df"}  -> HTTP 201
$ curl -X POST localhost:8001/counters/home-page
{"name":"home-page","value":3}  -> HTTP 200
$ curl localhost:8001/actors/1
{"actor_id":1,"first_name":"PENELOPE","last_name":"GUINESS"}  -> HTTP 200
$ curl localhost:8001/notes?customer_id=1
[{"customer_id":1,"text":"ligou a pedir um filme"},{"customer_id":1,"text":"nota da porta 8001"}]  -> HTTP 200
$ curl localhost:8001/counters/home-page
{"name":"home-page","value":3}  -> HTTP 200
############ instância B (porta 8002)
$ curl -X POST localhost:8002/actors -H Content-Type:application/json -d {"first_name": "GRACE", "last_name": "HOPPER"}
{"detail":"PostgreSQL: permission denied for table actor"}  -> HTTP 403
$ curl -X POST localhost:8002/notes -H Content-Type:application/json -d {"customer_id": 1, "text": "nota da porta 8002"}
{"detail":"MongoDB: not authorized on ex09 to execute command { insert: \"notes\", ordered: true, lsid: { id: UUID(\"b298624c-08ab-468c-9484-2ec32153c8fe\") }, $db: \"ex09\" }"}  -> HTTP 403
$ curl -X POST localhost:8002/counters/home-page
{"detail":"Redis: User ex09_reader has no permissions to run the 'incr' command"}  -> HTTP 403
$ curl localhost:8002/actors/1
{"actor_id":1,"first_name":"PENELOPE","last_name":"GUINESS"}  -> HTTP 200
$ curl localhost:8002/notes?customer_id=1
[{"customer_id":1,"text":"ligou a pedir um filme"},{"customer_id":1,"text":"nota da porta 8001"}]  -> HTTP 200
$ curl localhost:8002/counters/home-page
{"name":"home-page","value":3}  -> HTTP 200
```

| Pedido | A (8001) | B (8002) |
|---|---|---|
| `POST /actors` | 201 | **403** (PostgreSQL: permission denied) |
| `POST /notes` | 201 | **403** (MongoDB: not authorized) |
| `POST /counters/home-page` | 200 | **403** (Redis: no permissions to run 'incr') |
| `GET /actors/1` | 200 | 200 |
| `GET /notes?customer_id=1` | 200 | 200 |
| `GET /counters/home-page` | 200 | 200 |

A nota escrita pela A (`nota da porta 8001`) é lida pela B; o contador incrementado pela A tem o
mesmo valor nas duas. As três escritas da B foram recusadas pelos motores.
