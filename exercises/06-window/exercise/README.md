# Exercício 06 — Window functions e view materializada

Ficheiro: `queries.sql` (as 6 tarefas, cada uma com o número num comentário).

```bash
./scripts/create-db.sh ex06 --pagila --reset
docker compose exec -T postgres psql -U postgres -d ex06 -v ON_ERROR_STOP=1 < exercises/06-window/exercise/queries.sql
```

| # | Linhas | Esperado | Valores conferidos |
|---|---|---|---|
| 1 | 56 | 56 | empatados com a mesma posição |
| 2 | 28 | 28 | último `running_total` = 2409.88 |
| 3 | 55 | 55 | 2026-07: 2409.88, anterior 2105.73, `change` 304.15, `change_pct` 14.4 |
| 4 | 999 | 999 | loja 1: 468 com 344.06; loja 2: 526 com 358.12 |
| 5 | 10 | 10 | |

- **1** usa `DENSE_RANK`: filmes com o mesmo nº de alugueres ficam na mesma posição e entram todos os das posições 1 a 3.
- **3** a % é `round(100 * (receita - LAG(receita)) / LAG(receita), 1)`; o 1.º mês não tem anterior (vazio).
- **4** começa em `customer` com `LEFT JOIN payment` e `coalesce(sum, 0)`, por isso entram os 999 clientes; `RANK` dá a mesma posição a empatados.
- **5** usa `ROW_NUMBER` com desempate por `customer_id`, para ficarem exatamente 5 por loja.

**Tarefa 6.** O enunciado só lista as tarefas 1 a 5, mas os entregáveis falam de 6 tarefas e o
"Done when" de uma view materializada que só muda depois do refresh. A tarefa 6 é essa: a view
`monthly_revenue`, com índice único para `REFRESH ... CONCURRENTLY`.

## 1. Top 3 filmes por categoria (DENSE_RANK) — esperado 56 linhas

```
  category   | position |        title         | rentals 
-------------+----------+----------------------+---------
 Action      |        1 | CAT CONEHEADS        |     123
 Action      |        2 | SEABISCUIT PUNK      |      96
 Action      |        3 | IDOLS SNATCHERS      |      92
 Animation   |        1 | GILMORE BOILED       |     102
 Animation   |        1 | GRIT CLOCKWORK       |     102
...
(56 rows)
```

## 2. Receita por dia em julho de 2026 com total acumulado — esperado 28 linhas, último total 2409.88

```
    day     | revenue | running_total 
------------+---------+---------------
 2026-07-01 |   67.78 |         67.78
 2026-07-02 |   89.62 |        157.40
 2026-07-03 |   61.78 |        219.18
 2026-07-04 |   97.66 |        316.84
 2026-07-05 |   46.81 |        363.65
...
(28 rows)
```

## 3. Receita por mês com variação — esperado 55 linhas; julho 2026: 2409.88, anterior 2105.73, +304.15, 14.4%

```
   month    | revenue  | previous_month |  change  | change_pct 
------------+----------+----------------+----------+------------
 2022-01-01 |  3094.78 |                |          |           
 2022-02-01 | 10164.97 |        3094.78 |  7070.19 |      228.5
 2022-03-01 | 11413.86 |       10164.97 |  1248.89 |       12.3
 2022-04-01 | 10759.52 |       11413.86 |  -654.34 |       -5.7
 2022-05-01 | 11347.28 |       10759.52 |   587.76 |        5.5
...
(55 rows)
```

## 4. Posição de cada cliente no ranking da loja (RANK, sem pagamentos = 0) — esperado 999 linhas; 468 1.º na loja 1 (344.06), 526 1.º na loja 2 (358.12)

```
 store_id | position | customer_id | first_name  |  last_name   | total_paid 
----------+----------+-------------+-------------+--------------+------------
        1 |        1 |         468 | TIM         | CARY         |     344.06
        1 |        2 |         380 | RUSSELL     | BRINSON      |     324.04
        1 |        3 |         368 | HARRY       | ARCE         |     323.17
        1 |        4 |         295 | DAISY       | BATES        |     322.12
        1 |        5 |          22 | LAURA       | RODRIGUEZ    |     320.17
...
(999 rows)
```

## 5. Top 5 clientes de cada loja — esperado 10 linhas

```
 store_id | position | customer_id | first_name | last_name | total_paid 
----------+----------+-------------+------------+-----------+------------
        1 |        1 |         468 | TIM        | CARY      |     344.06
        1 |        2 |         380 | RUSSELL    | BRINSON   |     324.04
        1 |        3 |         368 | HARRY      | ARCE      |     323.17
        1 |        4 |         295 | DAISY      | BATES     |     322.12
        1 |        5 |          22 | LAURA      | RODRIGUEZ |     320.17
...
(10 rows)
```

## 6. View materializada `monthly_revenue`

```sql
CREATE MATERIALIZED VIEW monthly_revenue AS
SELECT date_trunc('month', payment_date)::date AS month, sum(amount) AS revenue, count(*) AS payments
FROM payment GROUP BY 1;
CREATE UNIQUE INDEX ON monthly_revenue (month);
```

Passos e output:

```
-- antes
   month    | revenue | payments
------------+---------+----------
 2026-07-01 | 2409.88 |      812

-- INSERT de um pagamento de 10.00 em 2026-07-30
INSERT 0 1

-- depois do INSERT, antes do refresh: igual
   month    | revenue | payments
------------+---------+----------
 2026-07-01 | 2409.88 |      812

REFRESH MATERIALIZED VIEW CONCURRENTLY monthly_revenue;

-- depois do refresh
   month    | revenue | payments
------------+---------+----------
 2026-07-01 | 2419.88 |      813
```

A view guarda o resultado da query: só muda com o `REFRESH`. O `CONCURRENTLY` deixa continuar a
ler a view durante o refresh e precisa do índice único em `month`.
