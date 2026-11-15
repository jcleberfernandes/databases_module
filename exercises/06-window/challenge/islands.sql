-- Challenge 06: gaps and islands
-- ./scripts/create-db.sh ch06 --pagila --reset
-- docker compose exec -T postgres psql -U postgres -d ch06 < exercises/06-window/challenge/islands.sql
-- Ilha = meses de calendário seguidos em que o cliente alugou pelo menos um filme.
-- Só window functions e operações de conjuntos: sem código procedimental nem CTE recursiva.

WITH months AS (
    -- uma linha por cliente e mês com alugueres (DISTINCT tira os repetidos)
    SELECT DISTINCT customer_id, date_trunc('month', rental_date)::date AS month
    FROM rental
),
numbered AS (
    -- nº do mês (ano * 12 + mês) menos o row_number: é igual em todos os meses da mesma ilha
    SELECT customer_id, month,
           (extract(year FROM month) * 12 + extract(month FROM month))
           - row_number() OVER (PARTITION BY customer_id ORDER BY month) AS island
    FROM months
),
islands AS (
    SELECT customer_id, min(month) AS first_month, max(month) AS last_month, count(*) AS months
    FROM numbered
    GROUP BY customer_id, island
),
longest AS (
    -- a ilha mais longa de cada cliente; em empate, a mais antiga
    SELECT *, row_number() OVER (PARTITION BY customer_id ORDER BY months DESC, first_month) AS pos
    FROM islands
)
SELECT customer_id, to_char(first_month, 'YYYY-MM') AS first_month,
       to_char(last_month, 'YYYY-MM') AS last_month, months
FROM longest
WHERE pos = 1
ORDER BY months DESC, customer_id
LIMIT 10;
