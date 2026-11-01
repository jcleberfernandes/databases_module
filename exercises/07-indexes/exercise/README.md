# Exercício 07 — Índices

Ficheiros:
- `create_big_rental.sql` — cria `big_rental` com 2 milhões de linhas (o script não vinha no repositório, por isso usei o SQL do tutorial).
- `indexes.sql` — as 5 queries: plano antes, índice, plano depois.

```bash
./scripts/create-db.sh ex07
docker compose exec -T postgres psql -U postgres -d ex07 -v ON_ERROR_STOP=1 < exercises/07-indexes/exercise/create_big_rental.sql
docker compose exec -T postgres psql -U postgres -d ex07 -v ON_ERROR_STOP=1 < exercises/07-indexes/exercise/indexes.sql
```

## Resumo

| # | Query | Índice | Antes | Depois |
|---|---|---|---|---|
| 1 | últimos 10 de um cliente | `(customer_id, rented_at DESC)` | 53.6 ms | 0.09 ms |
| 2 | um aluguer pelo `id` | `UNIQUE (id)` | 56.3 ms | 0.05 ms |
| 3 | por devolver há +30 dias | parcial `(rented_at) WHERE returned_at IS NULL` | 68.9 ms | 19.2 ms |
| 4 | alugueres de 1 dia | `(rented_at)` | 35.3 ms | 3.4 ms |
| 5 | últimos 2 anos (67% da tabela) | `(rented_at)` | 487 ms | **não ajuda** (forçado: 1698 ms) |

## Q1 — últimos 10 alugueres do cliente 42

```sql
SELECT * FROM big_rental WHERE customer_id = 42 ORDER BY rented_at DESC LIMIT 10;
```

Antes:
```
Limit (actual time=51.019..53.550 rows=10)
  -> Gather Merge -> Sort (top-N heapsort)
     -> Parallel Seq Scan on big_rental  Filter: (customer_id = 42)  Rows Removed by Filter: 665553
Execution Time: 53.603 ms
```

Índice: `CREATE INDEX big_rental_customer_rented ON big_rental (customer_id, rented_at DESC);`

Depois:
```
Limit (actual time=0.032..0.078 rows=10)
  -> Index Scan using big_rental_customer_rented  Index Cond: (customer_id = 42)
Execution Time: 0.089 ms
```

O índice já está ordenado por cliente e data, por isso o PostgreSQL lê só as 10 primeiras entradas em vez de ler os 2 milhões de linhas e ordenar.

## Q2 — um aluguer pelo id

```sql
SELECT * FROM big_rental WHERE id = 1234567;
```

Antes:
```
Gather -> Parallel Seq Scan on big_rental  Filter: (id = 1234567)  Rows Removed by Filter: 666666
Execution Time: 56.309 ms
```

Índice: `CREATE UNIQUE INDEX big_rental_id ON big_rental (id);`

Depois:
```
Index Scan using big_rental_id  Index Cond: (id = 1234567)  Buffers: shared read=4
Execution Time: 0.047 ms
```

A tabela foi criada com `CREATE TABLE AS`, sem chave primária; com o índice basta descer a árvore B (4 páginas) em vez de ler a tabela toda.

## Q3 — por devolver há mais de 30 dias

```sql
SELECT count(*) FROM big_rental WHERE returned_at IS NULL AND rented_at < now() - interval '30 days';
```

Antes:
```
Finalize Aggregate -> Gather -> Parallel Seq Scan  Filter: ((returned_at IS NULL) AND ...)  Rows Removed by Filter: 647186
Execution Time: 68.925 ms
```

Índice: `CREATE INDEX big_rental_open ON big_rental (rented_at) WHERE returned_at IS NULL;`

Depois:
```
Aggregate -> Index Only Scan using big_rental_open  Heap Fetches: 0  Buffers: shared hit=1 read=161
Execution Time: 19.154 ms
```

O índice parcial só guarda os ~3% de linhas por devolver: é pequeno (161 páginas) e chega para responder sem ler a tabela (Index Only Scan).

## Q4 — alugueres de um único dia

```sql
SELECT * FROM big_rental WHERE rented_at >= now() - interval '100 days' AND rented_at < now() - interval '99 days';
```

Antes (só existia o índice da Q1, que começa por `customer_id`):
```
Bitmap Heap Scan -> Bitmap Index Scan on big_rental_customer_rented  Index Searches: 601
Execution Time: 35.324 ms
```

Índice: `CREATE INDEX big_rental_rented ON big_rental (rented_at);`

Depois:
```
Bitmap Heap Scan -> Bitmap Index Scan on big_rental_rented  Index Searches: 1
Execution Time: 3.417 ms
```

Antes o PostgreSQL 18 usava o índice da Q1 com *skip scan* (601 pesquisas, uma por cliente); com um índice que começa por `rented_at` basta 1 pesquisa.

## Q5 — últimos 2 anos: o índice NÃO resolve

```sql
SELECT * FROM big_rental WHERE rented_at > now() - interval '730 days';
```

Com o índice `big_rental_rented` já criado, o planner escolhe na mesma:
```
Seq Scan on big_rental  rows=1334082  Rows Removed by Filter: 665918
Execution Time: 487.092 ms
```

Forçando o índice (`SET enable_seqscan = off; SET enable_bitmapscan = off;`):
```
Index Scan using big_rental_rented  rows=1334081  Buffers: shared hit=1333976 read=3648
Execution Time: 1698.153 ms
```

A query devolve 67% da tabela: com o índice o PostgreSQL faz um acesso à tabela por linha (1,3 milhões de leituras de páginas), enquanto o Seq Scan lê cada página uma só vez em sequência. Quando se pede quase tudo, nenhum índice ajuda; só ajudaria pedir menos linhas (ex: `LIMIT`) ou menos colunas.
