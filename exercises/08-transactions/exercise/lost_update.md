# Lost update (tarefas 1 e 2)

Duas sessões `psql` na base `ex08`, lado a lado:

```bash
docker compose exec postgres psql -U postgres -d ex08     # sessão A
docker compose exec postgres psql -U postgres -d ex08     # sessão B (noutro terminal)
```

Cada sessão quer tirar 10 ao saldo do cliente 1, que começa em 100.

## 1. O lost update

| Sessão A | Sessão B |
|---|---|
| `BEGIN;` | |
| `SELECT balance FROM customer WHERE customer_id = 1;` → **100.00** | |
| | `BEGIN;` |
| | `SELECT balance FROM customer WHERE customer_id = 1;` → **100.00** |
| `UPDATE customer SET balance = 90 WHERE customer_id = 1;` → `UPDATE 1` | |
| `COMMIT;` | |
| | `UPDATE customer SET balance = 90 WHERE customer_id = 1;` → `UPDATE 1` |
| | `COMMIT;` |

Saldo final: **90.00**. Devia ser 80: a B calculou `100 - 10` com um valor que já estava
desatualizado e escreveu por cima da A. Repor: `UPDATE customer SET balance = 100 WHERE customer_id = 1;`

## 2a. Correção com `UPDATE` atómico

| Sessão A | Sessão B |
|---|---|
| `BEGIN;` | |
| | `BEGIN;` |
| `UPDATE customer SET balance = balance - 10 WHERE customer_id = 1 AND balance >= 10;` → `UPDATE 1` | |
| | `UPDATE customer SET balance = balance - 10 WHERE customer_id = 1 AND balance >= 10;` → **fica à espera** |
| `COMMIT;` | |
| | → `UPDATE 1` (com o valor novo, 90) |
| | `COMMIT;` |

Saldo final: **80.00**. A conta é feita pela base de dados (`balance - 10`) sobre o valor atual.
Quando a B consegue o lock da linha, o PostgreSQL volta a ler a linha (já com 90) antes de a mudar.

## 2b. Correção com `SELECT ... FOR UPDATE`

| Sessão A | Sessão B |
|---|---|
| `BEGIN;` | |
| `SELECT balance FROM customer WHERE customer_id = 1 FOR UPDATE;` → **100.00** | |
| | `BEGIN;` |
| | `SELECT balance FROM customer WHERE customer_id = 1 FOR UPDATE;` → **fica à espera** |
| `UPDATE customer SET balance = 90 WHERE customer_id = 1;` → `UPDATE 1` | |
| `COMMIT;` | |
| | → **90.00** |
| | `UPDATE customer SET balance = 80 WHERE customer_id = 1;` → `UPDATE 1` |
| | `COMMIT;` |

Saldo final: **80.00**. O `FOR UPDATE` bloqueia a linha logo na leitura: a B só lê depois de a A
terminar, e por isso já lê 90.
