# Exercício 07 — Índices e otimização

Ficheiros: `setup.sql` (a tabela `big_rental` do enunciado) e `indexes.sql` (os `CREATE INDEX` que ficaram).

```bash
./scripts/create-db.sh ex07 --reset
docker compose exec -T postgres psql -U postgres -d ex07 -v ON_ERROR_STOP=1 < exercises/07-indexes/exercise/setup.sql
# medir as 5 queries com EXPLAIN (ANALYZE, BUFFERS), 3 vezes cada (mediana)
docker compose exec -T postgres psql -U postgres -d ex07 -v ON_ERROR_STOP=1 < exercises/07-indexes/exercise/indexes.sql
# medir outra vez
```

Cada query foi corrida 3 vezes com `EXPLAIN (ANALYZE, BUFFERS)`; os tempos são a mediana do `Execution Time`.

## Resumo

| Query | Plano antes | Índice | Plano depois | Mediana antes | Mediana depois |
|---|---|---|---|---|---|
| Q1 | Parallel Seq Scan | `(customer_id) WHERE returned_at IS NULL` | **Index Only Scan** | 68.4 ms | 0.08 ms |
| Q2 | Parallel Seq Scan + Sort | `(rented_at)` | **Bitmap Heap Scan** | 158.2 ms | 5.0 ms |
| Q3 | Parallel Seq Scan | nenhum (como está escrita) | Parallel Seq Scan | 133.8 ms | 112.6 ms |
| Q3 reescrita | — | `(rented_at)` | **Bitmap Heap Scan** | — | 5.1 ms |
| Q4 | Parallel Seq Scan + GroupAggregate | nenhum | Parallel Seq Scan | 175.1 ms | 172.3 ms |
| Q5 | Parallel Seq Scan + Sort | `(customer_id, rented_at)` | **Bitmap Heap Scan** (3 pesquisas no índice) | 73.6 ms | 1.9 ms |

## Q1

```sql
SELECT count(*) FROM big_rental WHERE customer_id = 42 AND returned_at IS NULL;
```

**O que devolve:** quantos alugueres do cliente 42 ainda não foram devolvidos (93).

Antes (mediana 68.4 ms; 50.3, 68.4, 70.7):
```
Finalize Aggregate -> Gather -> Partial Aggregate
  ->  Parallel Seq Scan on big_rental  (actual rows=31.00 loops=3)
        Filter: ((returned_at IS NULL) AND (customer_id = 42))
        Rows Removed by Filter: 666636
        Buffers: shared hit=2868 read=9868
```

Índice: `CREATE INDEX big_rental_open_customer ON big_rental (customer_id) WHERE returned_at IS NULL;`

Depois (mediana 0.08 ms):
```
  ->  Index Only Scan using big_rental_open_customer on big_rental  (actual rows=93.00 loops=1)
        Heap Fetches: 0
        Index Searches: 1
```

Sem índice, a tabela inteira (12 700 páginas) é lida para contar 93 linhas. O índice parcial só
tem os ~3% de linhas por devolver; para contar basta percorrer as entradas do cliente 42 no
índice, sem ir à tabela (Index Only Scan, `Heap Fetches: 0`).

## Q2

```sql
SELECT * FROM big_rental WHERE rented_at >= now() - interval '1 day' ORDER BY rented_at;
```

**O que devolve:** os alugueres das últimas 24 horas (~1 880), do mais antigo para o mais recente.

Antes (mediana 158.2 ms):
```
Gather Merge
  ->  Sort  (Sort Method: quicksort)
        ->  Parallel Seq Scan on big_rental  (actual rows=626.67 loops=3)
```

Índice: `CREATE INDEX big_rental_rented_at ON big_rental (rented_at);`

Depois (mediana 5.0 ms):
```
  ->  Bitmap Heap Scan on big_rental  (actual rows=1879.00 loops=1)
        ->  Bitmap Index Scan on big_rental_rented_at  (actual rows=1879.00 loops=1)
```

O índice encontra logo o intervalo do último dia (0,1% da tabela) e só essas páginas são lidas,
em vez de ler 2 milhões de linhas e ordenar as que sobram.

## Q3 — o índice não ajuda tal como está escrita

```sql
SELECT * FROM big_rental WHERE rented_at::date = current_date - 10;
```

**O que devolve:** os alugueres feitos há exatamente 10 dias (1 869).

Antes (mediana 133.8 ms):
```
  ->  Parallel Seq Scan on big_rental  (actual rows=623.00 loops=3)
        Filter: ((rented_at)::date = (CURRENT_DATE - 10))
```

Com o índice `(rented_at)` já criado, o plano é **o mesmo** (mediana 112.6 ms):
```
  ->  Parallel Seq Scan on big_rental  (actual rows=623.00 loops=3)
```

Porquê: o índice está ordenado por `rented_at`, mas o `WHERE` compara `rented_at::date`, o
resultado de uma conversão. Para usar o índice, o PostgreSQL teria de converter todas as linhas
primeiro. Um índice na própria expressão também não serve:

```
CREATE INDEX big_rental_rented_date ON big_rental ((rented_at::date));
ERROR:  functions in index expression must be marked IMMUTABLE
```

A conversão de `timestamptz` para `date` depende do fuso horário da sessão, por isso não é `IMMUTABLE`.

**Reescrita** (o mesmo dia como intervalo sobre a coluna, sem a converter):

```sql
SELECT * FROM big_rental
WHERE rented_at >= (current_date - 10)::timestamptz AND rented_at < (current_date - 9)::timestamptz;
```

Devolve as mesmas 1 869 linhas e usa o índice (mediana 5.1 ms):
```
Bitmap Heap Scan on big_rental  (actual rows=1869.00 loops=1)
  ->  Bitmap Index Scan on big_rental_rented_at  (actual rows=1869.00 loops=1)
        Index Cond: ((rented_at >= ((CURRENT_DATE - 10))::timestamp with time zone) AND (rented_at < ((CURRENT_DATE - 9))::timestamp with time zone))
```

## Q4 — nenhum índice compensa

```sql
SELECT customer_id, count(*) FROM big_rental WHERE returned_at IS NOT NULL GROUP BY customer_id;
```

**O que devolve:** para cada um dos 600 clientes, quantos alugueres já devolveu.

Antes (mediana 175.1 ms):
```
Finalize GroupAggregate -> Gather Merge -> Sort -> Partial HashAggregate
  ->  Parallel Seq Scan on big_rental  (actual rows=646640.00 loops=3)
```

Experimentei `CREATE INDEX ... ON big_rental (customer_id) WHERE returned_at IS NOT NULL;`.
O planner **continua a escolher o Seq Scan** (mediana 174.4 ms). Forçando o índice
(`SET enable_seqscan = off`), fica um Parallel Index Only Scan com mediana 143.1 ms:

```
  ->  Parallel Index Only Scan using big_rental_returned_customer  (actual rows=646640.00 loops=3)
        Heap Fetches: 0
```

A query precisa de **97% das linhas** (1,94 milhões). Seja pela tabela ou pelo índice, tem de as
ler quase todas e agrupá-las; o índice só poupa um pouco, por ser mais estreito do que a tabela.
Esse ganho não aparece sem forçar o planner, e o índice custa espaço e tempo em cada escrita
(ver o custo de escrita abaixo). Por isso não o mantive. Para esta pergunta ser rápida era preciso
outra abordagem, por exemplo guardar o resultado numa view materializada (sessão 06).

## Q5

```sql
SELECT * FROM big_rental
WHERE customer_id IN (7, 42, 99) AND rented_at >= now() - interval '30 days'
ORDER BY rented_at DESC;
```

**O que devolve:** os alugueres dos últimos 30 dias dos clientes 7, 42 e 99 (295), do mais recente para o mais antigo.

Antes (mediana 73.6 ms):
```
Gather Merge
  ->  Sort  (Sort Method: quicksort)
        ->  Parallel Seq Scan on big_rental  (actual rows=98.33 loops=3)
```

Índice: `CREATE INDEX big_rental_customer_rented ON big_rental (customer_id, rented_at);`

Depois (mediana 1.9 ms):
```
  ->  Bitmap Heap Scan on big_rental  (actual rows=295.00 loops=1)
        ->  Bitmap Index Scan on big_rental_customer_rented  (actual rows=295.00 loops=1)
              Index Searches: 3
```

Coluna da igualdade (`customer_id`) primeiro, coluna do intervalo (`rented_at`) depois: o índice
faz 3 pesquisas, uma por cliente, e em cada uma lê só os últimos 30 dias.

## Custo de escrita

`INSERT INTO big_rental SELECT g, 1, now(), NULL FROM generate_series(2000001, 2100000) g;`
(100 000 linhas), com a tabela recriada pelo `setup.sql` antes de cada execução:

| Tabela | Execuções | Mediana |
|---|---|---|
| sem índices | 106.4, 153.3, 136.4 ms | **136.4 ms** |
| com os 3 índices de `indexes.sql` | 594.6, 647.9, 607.7 ms | **607.7 ms** |

Com os 3 índices o `INSERT` é ~4,5× mais lento. Cada linha nova não é só escrita na tabela: é
também inserida em cada índice, no sítio certo da árvore B. Isto é o custo dos índices: leituras
muito mais rápidas, escritas mais lentas (e mais espaço). Por isso só se criam os índices que as
queries medidas realmente usam.
