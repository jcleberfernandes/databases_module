-- Challenge 06: gaps and islands
-- Para cada cliente, a maior sequência de meses consecutivos com pelo menos 1 aluguer.
-- Só window functions, sem código procedimental.

WITH months AS (
    -- 1 linha por cliente e mês com alugueres
    SELECT DISTINCT customer_id, date_trunc('month', rental_date)::date AS month
    FROM rental
),
numbered AS (
    -- Truque: mês (em nº de meses) menos row_number é constante dentro de uma sequência
    SELECT customer_id, month,
           (extract(year FROM month) * 12 + extract(month FROM month))
           - row_number() OVER (PARTITION BY customer_id ORDER BY month) AS island
    FROM months
),
islands AS (
    SELECT customer_id, island, min(month) AS start_month, max(month) AS end_month, count(*) AS months
    FROM numbered
    GROUP BY customer_id, island
),
best AS (
    -- a maior ilha de cada cliente (em empate, a mais antiga)
    SELECT *, row_number() OVER (PARTITION BY customer_id ORDER BY months DESC, start_month) AS pos
    FROM islands
)
SELECT b.customer_id, c.first_name, c.last_name, b.months, b.start_month, b.end_month
FROM best b
JOIN customer c ON c.customer_id = b.customer_id
WHERE b.pos = 1
ORDER BY b.months DESC, b.customer_id
LIMIT 10;
