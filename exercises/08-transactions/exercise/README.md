# Exercício 08 — Transações e concorrência

Ficheiros:
- `setup.sql` — coluna `balance` em `customer` e 20 funcionários ativos na loja 1.
- `sessions.py` — repete com duas ligações (A e B) as sequências 1, 2 e 3.
- `write_skew.py` — 20 pedidos em simultâneo (ponto 4).
- `db.py`, `pyproject.toml` — ligação (lê `POSTGRES_USER`/`POSTGRES_PASSWORD` do `.env` da raiz).

```bash
./scripts/create-db.sh ex08 --pagila
docker compose exec -T postgres psql -U postgres -d ex08 -v ON_ERROR_STOP=1 < exercises/08-transactions/exercise/setup.sql
cd exercises/08-transactions/exercise
uv run python sessions.py
uv run python write_skew.py ex08 read_committed
uv run python write_skew.py ex08 serializable
```

As sequências podem ser feitas à mão em dois terminais com
`docker compose exec postgres psql -U postgres -d ex08`; o `sessions.py` faz exatamente os mesmos passos.

## 1. Lost update

Cada sessão quer tirar 10 ao saldo de 100 do cliente 1.

| Sessão A | Sessão B |
|---|---|
| `BEGIN;` | |
| `SELECT balance FROM customer WHERE customer_id = 1;` → 100 | |
| | `BEGIN;` |
| | `SELECT balance FROM customer WHERE customer_id = 1;` → 100 |
| `UPDATE customer SET balance = 90 WHERE customer_id = 1;` | |
| `COMMIT;` | |
| | `UPDATE customer SET balance = 90 WHERE customer_id = 1;` |
| | `COMMIT;` |

Saldo final: **90**. Devia ser 80: a escrita de A perdeu-se, porque B calculou o valor com uma leitura antiga.

## 2. Correções

**a) UPDATE atómico** — o cálculo é feito pela base de dados, não pela aplicação:

| Sessão A | Sessão B |
|---|---|
| `BEGIN;` | `BEGIN;` |
| `UPDATE customer SET balance = balance - 10 WHERE customer_id = 1 AND balance >= 10;` | |
| | o mesmo `UPDATE` → fica à espera do lock de A |
| `COMMIT;` | |
| | o `UPDATE` continua com o valor novo (90 → 80) |
| | `COMMIT;` |

Saldo final: **80**.

**b) SELECT ... FOR UPDATE** — a leitura bloqueia a linha:

| Sessão A | Sessão B |
|---|---|
| `BEGIN;` | |
| `SELECT balance FROM customer WHERE customer_id = 1 FOR UPDATE;` → 100 | |
| | `BEGIN;` |
| | `SELECT balance FROM customer WHERE customer_id = 1 FOR UPDATE;` → fica à espera |
| `UPDATE customer SET balance = 90 WHERE customer_id = 1;` | |
| `COMMIT;` | |
| | → devolve 90 |
| | `UPDATE customer SET balance = 80 WHERE customer_id = 1;` |
| | `COMMIT;` |

Saldo final: **80**.

## 3. Deadlock

| Sessão A | Sessão B |
|---|---|
| `BEGIN;` | `BEGIN;` |
| `UPDATE customer SET balance = balance - 10 WHERE customer_id = 1;` | |
| | `UPDATE customer SET balance = balance - 10 WHERE customer_id = 2;` |
| `UPDATE customer SET balance = balance - 10 WHERE customer_id = 2;` → espera por B | |
| | `UPDATE customer SET balance = balance - 10 WHERE customer_id = 1;` → espera por A |

```
ERROR:  deadlock detected
DETAIL:  Process 1935 waits for ShareLock on transaction 1468; blocked by process 1936.
Process 1936 waits for ShareLock on transaction 1467; blocked by process 1935.
HINT:  See server log for query details.
CONTEXT:  while locking tuple (17,33) in relation "customer"
```

A tem a linha 1 e quer a 2; B tem a 2 e quer a 1. Ninguém pode avançar.
Depois de ~1 s (`deadlock_timeout`) o PostgreSQL deteta o ciclo e cancela uma
das transações (aqui a A), que tem de fazer `ROLLBACK`; a outra (B) continua e faz `COMMIT`.
O `DETAIL` diz que processo espera por qual, e o `CONTEXT` a linha (tuple) em que bloqueou.
Para evitar: bloquear as linhas sempre pela mesma ordem (ex: por `customer_id`).

## 4. Write skew

Regra: cada loja tem pelo menos 1 funcionário ativo. Cada um dos 20 pedidos
conta os ativos da loja 1 e, se houver mais de 1, desativa o seu funcionário.

```
READ COMMITTED: 20 funcionários ativos na loja 1
desativados=20 recusados=0 retries=0
ativos no fim: 0  ->  REGRA QUEBRADA

SERIALIZABLE: 20 funcionários ativos na loja 1
desativados=19 recusados=1 retries=227
ativos no fim: 1  ->  regra cumprida
```

Em `READ COMMITTED` todos leem "20 ativos" ao mesmo tempo e todos desativam
(cada um mexe numa linha diferente, por isso nenhum lock os trava).
Em `SERIALIZABLE` o PostgreSQL deteta que as leituras e escritas se cruzam e
cancela transações com `SerializationFailure`; o script repete-as e, ao
repetir, elas veem o número atualizado. Fica **exatamente 1** ativo.
