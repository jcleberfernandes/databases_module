# Challenge 07 — OFFSET vs keyset, INCLUDE e VACUUM

Ficheiro: `pagination.sql` (todas as instruções, por ordem).

```bash
./scripts/create-db.sh ch07 --reset
docker compose exec -T postgres psql -U postgres -d ch07 -v ON_ERROR_STOP=1 < exercises/07-indexes/exercise/setup.sql
docker compose exec -T postgres psql -U postgres -d ch07 -v ON_ERROR_STOP=1 < exercises/07-indexes/challenge/pagination.sql
```

Páginas de 20 linhas da tabela inteira por `rented_at DESC, id DESC`; a página 5 000 começa
depois de 99 980 linhas.

## 1. Índice com a ordem da paginação

```sql
CREATE INDEX big_rental_page ON big_rental (rented_at DESC, id DESC);
```

## 2. OFFSET — página 5 000

```sql
SELECT id, rented_at, customer_id FROM big_rental
ORDER BY rented_at DESC, id DESC OFFSET 99980 LIMIT 20;
```
```
 Limit  (actual time=152.119..152.131 rows=20.00 loops=1)
   ->  Index Scan using big_rental_page on big_rental  (actual time=0.260..148.183 rows=100000.00 loops=1)
         Buffers: shared hit=87572 read=12805 written=1862
 Execution Time: 152.146 ms
```

## 3. Keyset — página 5 000

```sql
SELECT rented_at AS last_rented_at, id AS last_id
FROM big_rental ORDER BY rented_at DESC, id DESC OFFSET 99979 LIMIT 1 \gset

SELECT id, rented_at, customer_id FROM big_rental
WHERE (rented_at, id) < (:'last_rented_at', :last_id)
ORDER BY rented_at DESC, id DESC LIMIT 20;
```
```
 Limit  (actual time=0.049..0.069 rows=20.00 loops=1)
   ->  Index Scan using big_rental_page on big_rental  (actual time=0.048..0.066 rows=20.00 loops=1)
         Index Cond: (ROW(rented_at, id) < ROW('2026-09-11 14:10:33.279065+00'::timestamp with time zone, 13584))
         Buffers: shared hit=22 read=1
 Execution Time: 0.118 ms
```

**As mesmas 20 linhas:** um `EXCEPT` entre as duas queries dá `differences = 0`.

| | OFFSET | Keyset |
|---|---|---|
| linhas lidas no índice | 100 000 | 20 |
| páginas lidas (buffers) | ~100 000 | 23 |
| tempo | 152.1 ms | 0.12 ms |

**O keyset não depende da página.** A mesma comparação na página 50 000 (depois de 999 980 linhas):

```
-- keyset
 Limit  (actual time=0.029..0.051 rows=20.00 loops=1)
   ->  Index Scan using big_rental_page on big_rental  (actual rows=20.00 loops=1)
         Buffers: shared hit=22 read=1
 Execution Time: 0.065 ms

-- OFFSET 999980
 Limit  (actual time=1150.561..1150.596 rows=20.00 loops=1)
   ->  Index Scan using big_rental_page on big_rental  (actual rows=1000000.00 loops=1)
         Buffers: shared hit=1000243 read=3507 written=669
 Execution Time: 1150.619 ms
```

O keyset demora o mesmo (~0,1 ms) na página 5 000 e na 50 000; o OFFSET passa de 152 ms para 1 150 ms.

**Porque o OFFSET fica mais lento quanto mais à frente está a página.** O `OFFSET n` não salta
diretamente para a linha n: o PostgreSQL tem de ler as n linhas pela ordem, uma a uma, e deitá-las
fora. Na página 5 000 lê 100 000 linhas para devolver 20; na 50 000 lê 1 000 000. O custo cresce
com o número da página. O keyset usa o valor da última linha vista
(`(rented_at, id) < (...)`) como condição no índice: desce a árvore B até essa posição e lê só as
20 linhas seguintes, seja qual for a página.

## 4. `INCLUDE (customer_id)` → Index Only Scan

```sql
DROP INDEX big_rental_page;
CREATE INDEX big_rental_page ON big_rental (rented_at DESC, id DESC) INCLUDE (customer_id);
```
```
 Limit  (actual time=0.045..0.049 rows=20.00 loops=1)
   ->  Index Only Scan using big_rental_page on big_rental  (actual rows=20.00 loops=1)
         Heap Fetches: 0
         Buffers: shared hit=1 read=3
 Execution Time: 0.062 ms
```

A query só pede `id`, `rented_at` e `customer_id`, e agora as três estão no índice: não é preciso
ir à tabela (4 páginas lidas em vez de 23).

## 5. `UPDATE` e `VACUUM`

Depois de `UPDATE big_rental SET customer_id = customer_id WHERE id % 50 = 0;`:

```
   ->  Index Only Scan using big_rental_page on big_rental  (actual rows=20.00 loops=1)
         Heap Fetches: 20
         Buffers: shared hit=18 read=6 dirtied=6 written=6
 Execution Time: 0.300 ms
```

Depois de `VACUUM big_rental;`:

```
   ->  Index Only Scan using big_rental_page on big_rental  (actual rows=20.00 loops=1)
         Heap Fetches: 0
         Buffers: shared hit=4
 Execution Time: 0.052 ms
```

**O que o `VACUUM` muda.** Mesmo num Index Only Scan, o PostgreSQL tem de saber se cada linha é
visível para a transação atual, e essa informação está na tabela, não no índice. Para não ir à
tabela, consulta o **visibility map**: um bit por página da tabela que diz "todas as linhas desta
página são visíveis para toda a gente". Se o bit está ligado, a linha do índice serve sem ir à
tabela; se não, faz um *heap fetch*.

O `UPDATE` (mesmo sem mudar o valor) cria uma versão nova de 1 em cada 50 linhas e deixa a antiga
para trás, por isso as páginas tocadas deixam de estar "all-visible" no visibility map: daí os 20
`Heap Fetches`. O `VACUUM` limpa as versões antigas e volta a ligar o bit dessas páginas, e o
`Heap Fetches` volta a 0. Sem `VACUUM` (ou autovacuum), um Index Only Scan vai à tabela como um
Index Scan normal.
