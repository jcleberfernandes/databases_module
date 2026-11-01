-- Exercício 06: window functions e views
-- ./scripts/create-db.sh ex06 --pagila
-- docker compose exec -T postgres psql -U postgres -d ex06 -v ON_ERROR_STOP=1 < exercises/06-window/exercise/queries.sql

-- 1. Top 3 filmes por categoria (por nº de alugueres).
-- DENSE_RANK: filmes empatados ficam com a mesma posição e entram todos.
WITH film_rentals AS (
    SELECT c.name AS category, f.title, count(r.rental_id) AS rentals
    FROM film f
    JOIN film_category fc ON fc.film_id = f.film_id
    JOIN category c       ON c.category_id = fc.category_id
    LEFT JOIN inventory i ON i.film_id = f.film_id
    LEFT JOIN rental r    ON r.inventory_id = i.inventory_id
    GROUP BY c.name, f.film_id
),
ranked AS (
    SELECT *, DENSE_RANK() OVER (PARTITION BY category ORDER BY rentals DESC) AS pos
    FROM film_rentals
)
SELECT category, pos, title, rentals
FROM ranked
WHERE pos <= 3
ORDER BY category, pos, title;

-- 2. Receita acumulada por dia
SELECT day, revenue,
       sum(revenue) OVER (ORDER BY day) AS cumulative_revenue
FROM (
    SELECT payment_date::date AS day, sum(amount) AS revenue
    FROM payment
    GROUP BY 1
) d
ORDER BY day
LIMIT 15;

-- 3. Variação face ao mês anterior
SELECT month, revenue,
       LAG(revenue) OVER (ORDER BY month) AS previous_month,
       revenue - LAG(revenue) OVER (ORDER BY month) AS change,
       round(100.0 * (revenue - LAG(revenue) OVER (ORDER BY month))
             / LAG(revenue) OVER (ORDER BY month), 1) AS change_pct
FROM (
    SELECT date_trunc('month', payment_date)::date AS month, sum(amount) AS revenue
    FROM payment
    GROUP BY 1
) m
ORDER BY month;

-- 4. Posição de cada cliente no ranking da sua loja (por valor gasto)
SELECT c.store_id, c.customer_id, c.first_name, c.last_name, sum(p.amount) AS total,
       RANK() OVER (PARTITION BY c.store_id ORDER BY sum(p.amount) DESC) AS store_position
FROM customer c
JOIN payment p ON p.customer_id = c.customer_id
GROUP BY c.customer_id
ORDER BY c.store_id, store_position
LIMIT 20;

-- 5. View materializada da receita mensal, com refresh
DROP MATERIALIZED VIEW IF EXISTS monthly_revenue;
CREATE MATERIALIZED VIEW monthly_revenue AS
SELECT date_trunc('month', payment_date)::date AS month, sum(amount) AS revenue, count(*) AS payments
FROM payment
GROUP BY 1;
-- índice único: necessário para REFRESH ... CONCURRENTLY (não bloqueia as leituras)
CREATE UNIQUE INDEX ON monthly_revenue (month);

SELECT * FROM monthly_revenue WHERE month = '2022-03-01';
-- Um pagamento novo não aparece na view até ao refresh
INSERT INTO payment (customer_id, staff_id, rental_id, amount, payment_date)
VALUES (1, 1, 1, 100.00, '2022-03-15');
SELECT * FROM monthly_revenue WHERE month = '2022-03-01';   -- igual a antes
REFRESH MATERIALIZED VIEW CONCURRENTLY monthly_revenue;
SELECT * FROM monthly_revenue WHERE month = '2022-03-01';   -- +100.00 e +1 pagamento
