-- Exercício 06: window functions e view materializada
-- ./scripts/create-db.sh ex06 --pagila --reset
-- docker compose exec -T postgres psql -U postgres -d ex06 -v ON_ERROR_STOP=1 < exercises/06-window/exercise/queries.sql

-- 1. Os 3 filmes mais alugados de cada categoria; empatados partilham a posição (DENSE_RANK)
WITH film_rentals AS (
    SELECT c.name AS category, f.film_id, f.title, count(r.rental_id) AS rentals
    FROM film f
    JOIN film_category fc ON fc.film_id = f.film_id
    JOIN category c       ON c.category_id = fc.category_id
    LEFT JOIN inventory i ON i.film_id = f.film_id
    LEFT JOIN rental r    ON r.inventory_id = i.inventory_id
    GROUP BY c.name, f.film_id, f.title
),
ranked AS (
    SELECT *, DENSE_RANK() OVER (PARTITION BY category ORDER BY rentals DESC) AS position
    FROM film_rentals
)
SELECT category, position, title, rentals
FROM ranked
WHERE position <= 3
ORDER BY category, position, title;

-- 2. Receita por dia em julho de 2026, com o total acumulado do mês
SELECT day, revenue, sum(revenue) OVER (ORDER BY day) AS running_total
FROM (
    SELECT payment_date::date AS day, sum(amount) AS revenue
    FROM payment
    WHERE payment_date >= '2026-07-01' AND payment_date < '2026-08-01'
    GROUP BY 1
) d
ORDER BY day;

-- 3. Receita por mês, com a variação face ao mês anterior (valor e %, 1 casa decimal)
SELECT month, revenue,
       LAG(revenue) OVER (ORDER BY month) AS previous_month,
       revenue - LAG(revenue) OVER (ORDER BY month) AS change,
       round(100 * (revenue - LAG(revenue) OVER (ORDER BY month)) / LAG(revenue) OVER (ORDER BY month), 1) AS change_pct
FROM (
    SELECT date_trunc('month', payment_date)::date AS month, sum(amount) AS revenue
    FROM payment
    GROUP BY 1
) m
ORDER BY month;

-- 4. Posição de cada cliente no ranking da sua loja pelo total pago
-- (sem pagamentos conta 0; empatados partilham a posição: RANK)
WITH paid AS (
    SELECT c.customer_id, c.store_id, c.first_name, c.last_name, coalesce(sum(p.amount), 0) AS total_paid
    FROM customer c
    LEFT JOIN payment p ON p.customer_id = c.customer_id
    GROUP BY c.customer_id
)
SELECT store_id, RANK() OVER (PARTITION BY store_id ORDER BY total_paid DESC) AS position,
       customer_id, first_name, last_name, total_paid
FROM paid
ORDER BY store_id, position, customer_id;

-- 5. Os 5 melhores clientes de cada loja pelo total pago
WITH paid AS (
    SELECT c.customer_id, c.store_id, c.first_name, c.last_name, coalesce(sum(p.amount), 0) AS total_paid
    FROM customer c
    LEFT JOIN payment p ON p.customer_id = c.customer_id
    GROUP BY c.customer_id
),
ranked AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY store_id ORDER BY total_paid DESC, customer_id) AS position
    FROM paid
)
SELECT store_id, position, customer_id, first_name, last_name, total_paid
FROM ranked
WHERE position <= 5
ORDER BY store_id, position;

-- 6. View materializada da receita mensal, e refresh
CREATE MATERIALIZED VIEW monthly_revenue AS
SELECT date_trunc('month', payment_date)::date AS month, sum(amount) AS revenue, count(*) AS payments
FROM payment
GROUP BY 1;
-- índice único: obrigatório para REFRESH ... CONCURRENTLY (as leituras continuam durante o refresh)
CREATE UNIQUE INDEX ON monthly_revenue (month);

SELECT * FROM monthly_revenue WHERE month = '2026-07-01';
-- um pagamento novo em julho de 2026
INSERT INTO payment (customer_id, staff_id, rental_id, amount, payment_date)
VALUES (1, 2, 76, 10.00, '2026-07-30 12:00+00');
SELECT * FROM monthly_revenue WHERE month = '2026-07-01';   -- ainda igual: a view guarda o resultado antigo
REFRESH MATERIALIZED VIEW CONCURRENTLY monthly_revenue;
SELECT * FROM monthly_revenue WHERE month = '2026-07-01';   -- agora com +10.00 e +1 pagamento
