# Exercício 09 — Segurança

Ficheiros:
- `roles.sql` — tarefa 1 (roles `ex09_migrations`, `ex09_app`, `ex09_readonly` e permissões).
- `proofs.sql` — tarefa 2.
- `users.sh` — corre o `roles.sql` com as passwords do `.env` e cria o utilizador do MongoDB e o do Redis.
- `api/` — a API (FastAPI): `main.py`, `pyproject.toml`.
- `.env.example` — todas as variáveis de que o `users.sh` e a API precisam.

**Nota sobre o enunciado:** fala em "users of tasks 1 and 3", "task 5" e "task 6", mas só tem 4
tarefas e nenhuma cria os utilizadores do MongoDB e do Redis. Como a API tem de escrever em cada
motor com um utilizador de privilégios mínimos, o `users.sh` cria-os: `ex09_app` no MongoDB
(`readWrite` só na base `ex09`) e `ex09_app` no Redis (ACL: só `INCR` em chaves `counter:*`).
A secção "Utilizadores do MongoDB e do Redis" mostra o que eles não podem fazer.

## Como correr

```bash
./scripts/create-db.sh ex09 --pagila --reset
cp exercises/09-security/exercise/.env.example exercises/09-security/exercise/.env   # e mudar as passwords
bash exercises/09-security/exercise/users.sh
docker compose exec -T postgres psql -U postgres -d ex09 < exercises/09-security/exercise/proofs.sql
cd exercises/09-security/exercise/api
uv run uvicorn main:app --port 8009
```

As credenciais vêm só de variáveis de ambiente (o `.env`, que nunca vai para o git). As passwords
de administrador nunca aparecem nos ficheiros: o `users.sh` usa as que os contentores já têm.
O `roles.sql` recebe as passwords com `psql -v app_password=...`.

## Tarefa 2 — `proofs.sql`

```
SET
ERROR:  must be owner of table film
INSERT 0 1
RESET
SET
 count 
-------
  1000
(1 row)

ERROR:  permission denied for table actor
RESET
```

| Como | Instrução | Esperado | Resultado |
|---|---|---|---|
| `ex09_app` | `DROP TABLE film` | falha | `ERROR: must be owner of table film` |
| `ex09_app` | `INSERT INTO actor ...` | funciona | `INSERT 0 1` |
| `ex09_readonly` | `SELECT count(*) FROM film` | funciona | `1000` |
| `ex09_readonly` | `INSERT INTO actor ...` | falha | `ERROR: permission denied for table actor` |

## API — os 3 endpoints

- `POST /actors`: `INSERT ... VALUES (%s, %s)` com parâmetros, como `ex09_app`. `201` com o `actor_id`.
- `POST /notes`: o corpo é validado com `StrictInt` / `StrictStr` (Pydantic em modo estrito:
  `"1"` ou um objeto não são convertidos), e o documento é inserido em `ex09.notes` como `ex09_app`. Outro tipo → `422`.
- `POST /counters/{name}`: o `name` tem de casar com `^[a-z0-9_-]{1,32}$` (`Path(pattern=...)`), senão `422`;
  depois `INCR counter:{name}` como `ex09_app`.

Pedidos normais:

```
$ curl -X POST localhost:8009/actors -H Content-Type: application/json -d {"first_name": "ADA", "last_name": "LOVELACE"}
{"actor_id":202}
-> HTTP 201

$ curl -X POST localhost:8009/notes -H Content-Type: application/json -d {"customer_id": 1, "text": "ligou a pedir um filme"}
{"_id":"6aec6da1857aae253437202b"}
-> HTTP 201

$ curl -X POST localhost:8009/counters/home-page
{"name":"home-page","value":1}
-> HTTP 200

$ curl -X POST localhost:8009/counters/home-page
{"name":"home-page","value":2}
-> HTTP 200

```

## Tarefa 4 — provas de que a API é segura

```
$ curl -X POST localhost:8009/actors -H Content-Type: application/json -d {"first_name": "x'); DROP TABLE actor; --", "last_name": "y"}
{"actor_id":203}
-> HTTP 201

$ curl -X POST localhost:8009/notes -H Content-Type: application/json -d {"customer_id": 1, "text": {"$ne": null}}
{"detail":[{"type":"string_type","loc":["body","text"],"msg":"Input should be a valid string","input":{"$ne":null}}]}
-> HTTP 422

$ curl -X POST localhost:8009/counters/a*
{"detail":[{"type":"string_pattern_mismatch","loc":["path","name"],"msg":"String should match pattern '^[a-z0-9_-]{1,32}$'","input":"a*","ctx":{"pattern":"^[a-z0-9_-]{1,32}$"}}]}
-> HTTP 422

$ curl -X POST localhost:8009/counters/x:y
{"detail":[{"type":"string_pattern_mismatch","loc":["path","name"],"msg":"String should match pattern '^[a-z0-9_-]{1,32}$'","input":"x:y","ctx":{"pattern":"^[a-z0-9_-]{1,32}$"}}]}
-> HTTP 422

```

O que ficou guardado:

```
-- PostgreSQL: o texto ficou guardado tal e qual, e actor continua a existir
 actor_id |        first_name         | last_name
----------+---------------------------+-----------
      203 | x'); DROP TABLE actor; -- | y
      202 | ADA                       | LOVELACE

 actors
--------
    203

-- MongoDB (ex09.notes): só a nota válida; a de {"$ne": null} nem chegou à base
[ { customer_id: 1, text: 'ligou a pedir um filme' } ]

-- Redis: só a chave válida; a* e x:y nunca chegaram ao Redis
GET counter:home-page  -> 2
counter:*              -> counter:home-page
```

- O `first_name` com `'); DROP TABLE actor; --` é enviado ao PostgreSQL como **valor** (`%s`), separado do SQL: nunca é executado.
- `{"$ne": null}` é um operador do MongoDB: se chegasse a uma query, mudava o seu significado.
  Com `StrictStr` é recusado antes de chegar à base.
- `a*` e `x:y` são recusados pelo padrão: o `*` é um padrão de chaves do Redis e o `:` permitia
  escrever fora do "espaço" `counter:` (por exemplo `counter:x:y`).

## Utilizadores do MongoDB e do Redis — o que não podem fazer

```
-- Redis, como ex09_app
FLUSHALL         -> NOPERM User ex09_app has no permissions to run the 'flushall' command
SET counter:x 1  -> NOPERM User ex09_app has no permissions to run the 'set' command
INCR other:x     -> NOPERM No permissions to access a key

-- MongoDB, como ex09_app: ler outra base
db.getSiblingDB("pagila_docs").films.findOne()  -> Unauthorized
```

## `ACL SETUSER` não sobrevive a um reinício do Redis

O `ACL SETUSER` só muda a configuração em memória: se o Redis reiniciar, o utilizador `ex09_app`
desaparece e a API deixa de conseguir escrever. Para o guardar:

- arrancar o Redis com um ficheiro de ACL (`--aclfile /data/users.acl` no `command` do
  `docker-compose.yml`, com o ficheiro num volume) e correr `ACL SAVE` depois do `ACL SETUSER`; ou
- pôr a linha `user ex09_app on >... ~counter:* +incr` no `redis.conf`;
- (neste repositório, sem mudar o compose) voltar a correr o `users.sh` depois de cada reinício.

O ficheiro de ACL é a melhor opção: as passwords ficam guardadas com hash e o `ACL SAVE` mantém-no atualizado.
