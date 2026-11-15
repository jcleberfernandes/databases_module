-- Exercício 15: view materializada usada pelo refresh.py (a do exercício 06)
CREATE MATERIALIZED VIEW monthly_revenue AS
SELECT date_trunc('month', payment_date)::date AS month, sum(amount) AS revenue
FROM payment
GROUP BY 1;

CREATE UNIQUE INDEX ON monthly_revenue (month);
