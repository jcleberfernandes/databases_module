# Deadlock (tarefa 3)

Duas sessões `psql` na base `ex08`. A atualiza o cliente 1 e depois o 2; B atualiza o 2 e depois o 1.

| Sessão A | Sessão B |
|---|---|
| `BEGIN;` | |
| | `BEGIN;` |
| `UPDATE customer SET balance = balance - 10 WHERE customer_id = 1;` → `UPDATE 1` | |
| | `UPDATE customer SET balance = balance - 10 WHERE customer_id = 2;` → `UPDATE 1` |
| `UPDATE customer SET balance = balance - 10 WHERE customer_id = 2;` → **fica à espera** (a B tem a linha 2) | |
| | `UPDATE customer SET balance = balance - 10 WHERE customer_id = 1;` → **fica à espera** (a A tem a linha 1) |
| ~1 s depois: **`ERROR: deadlock detected`** | → `UPDATE 1` (a A largou a linha 1) |
| `COMMIT;` → `ROLLBACK` | |
| | `COMMIT;` |

Resultado: a transação A foi cancelada (o `COMMIT` de uma transação com erro faz `ROLLBACK`) e
a B terminou. Clientes 1 e 2 ficam com 90.00 (só as alterações da B ficaram).

## A mensagem completa

```
ERROR:  deadlock detected
DETAIL:  Process 5477 waits for ShareLock on transaction 89013; blocked by process 5478.
Process 5478 waits for ShareLock on transaction 89012; blocked by process 5477.
HINT:  See server log for query details.
CONTEXT:  while locking tuple (17,20) in relation "customer"
```

Linha a linha:

- **`ERROR: deadlock detected`** — o PostgreSQL encontrou um ciclo de esperas e cancelou esta
  transação (a A) para os outros poderem continuar.
- **`Process 5477 waits for ShareLock on transaction 89013; blocked by process 5478.`** — o
  processo 5477 (a sessão A) está à espera que a transação 89013 (a da B) termine, porque a B
  tem a linha que a A quer mudar. Esperar por uma linha bloqueada é pedir um `ShareLock` no
  número da transação que a tem.
- **`Process 5478 waits for ShareLock on transaction 89012; blocked by process 5477.`** — e o
  processo 5478 (a B) está à espera da transação 89012 (a da A). As duas esperam uma pela outra:
  ninguém pode avançar.
- **`HINT: See server log for query details.`** — o log do servidor tem o SQL que cada processo
  estava a correr.
- **`CONTEXT: while locking tuple (17,20) in relation "customer"`** — a A ficou presa ao tentar
  bloquear a linha que está na página 17, posição 20, da tabela `customer` (é a linha do cliente 2).

O PostgreSQL só procura deadlocks depois de uma espera de `deadlock_timeout` (1 s por omissão).

## Como evitar

Fazer com que todas as transações bloqueiem as linhas **pela mesma ordem**, por exemplo sempre
por `customer_id` crescente (as duas sessões atualizavam primeiro o 1 e depois o 2). Assim a
segunda espera pela primeira, mas nunca há um ciclo. Ajuda também ter transações curtas, e
bloquear tudo o que é preciso logo no início (`SELECT ... WHERE customer_id IN (1, 2) ORDER BY
customer_id FOR UPDATE`). Mesmo assim, a aplicação deve estar preparada para repetir uma
transação cancelada por deadlock.
