# Challenge 07 — OFFSET vs keyset

Ficheiro: `pagination.sql` (corre na base `ex07`, depois do `create_big_rental.sql`).

```bash
docker compose exec -T postgres psql -U postgres -d ex07 -v ON_ERROR_STOP=1 < exercises/07-indexes/challenge/pagination.sql
```

A página 5000 (20 linhas) são as linhas 99 981 a 100 000. Os clientes de
`big_rental` têm ~3 300 alugueres cada, por isso o script cria o cliente 9999
com 200 000 alugueres. Índice usado: `(customer_id, rented_at DESC, id DESC)`.

## OFFSET — página 5000

```sql
SELECT * FROM big_rental WHERE customer_id = 9999
ORDER BY rented_at DESC, id DESC OFFSET 99980 LIMIT 20;
```
```
Limit (actual time=54.720..54.731 rows=20)
  -> Index Scan using big_rental_keyset  (actual rows=100000)  Buffers: shared hit=99930 read=495
Execution Time: 54.754 ms
```

O PostgreSQL lê 100 000 linhas e deita fora 99 980. Cada página seguinte é mais lenta.

## Keyset — página 5000

A aplicação guarda o `rented_at` e o `id` da última linha da página anterior (no script, com `\gset`):

```sql
SELECT * FROM big_rental
WHERE customer_id = 9999 AND (rented_at, id) < (:last_rented_at, :last_id)
ORDER BY rented_at DESC, id DESC LIMIT 20;
```
```
Limit (actual time=0.018..0.041 rows=20)
  -> Index Scan using big_rental_keyset  Index Cond: ((customer_id = 9999) AND (ROW(rented_at, id) < ROW(...)))
     Buffers: shared hit=22 read=1
Execution Time: 0.069 ms
```

Vai direto à posição certa no índice e lê só 20 linhas: **~800× mais rápido**,
e o tempo é o mesmo para a página 1 ou a 5000. As duas queries dão as mesmas
20 linhas (`differences = 0`).

## INCLUDE → Index Only Scan

`SELECT *` precisa de `returned_at`, que não está no índice, por isso o Index
Scan tem de ir à tabela. Com `INCLUDE` a coluna fica guardada no índice:

```sql
CREATE INDEX big_rental_keyset_cover ON big_rental (customer_id, rented_at DESC, id DESC) INCLUDE (returned_at);
```
```
Index Only Scan using big_rental_keyset_cover
  Heap Fetches: 0   Buffers: shared hit=1 read=3
Execution Time: 0.049 ms
```

## VACUUM e "Heap Fetches"

Mesmo num Index Only Scan, o PostgreSQL tem de confirmar que a linha é visível
para a transação. Ele consulta o *visibility map*: se a página está marcada
"all-visible", não precisa de ir à tabela. Quem marca as páginas é o `VACUUM`.

Depois de um `UPDATE` (com autovacuum desligado), as páginas deixam de estar
marcadas e o plano volta a ir à tabela:

```
Index Only Scan using big_rental_keyset_cover
  Heap Fetches: 40
Execution Time: 0.265 ms
```

Depois de `VACUUM big_rental`:

```
Index Only Scan using big_rental_keyset_cover
  Heap Fetches: 0
Execution Time: 0.047 ms
```

Ou seja: sem `VACUUM` (ou autovacuum) um "Index Only Scan" acaba por ler a tabela na mesma.
