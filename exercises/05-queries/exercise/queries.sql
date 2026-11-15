-- Exercício 05: 10 perguntas de negócio em Pagila (sem window functions)
-- ./scripts/create-db.sh ex05 --pagila --reset
-- docker compose exec -T postgres psql -U postgres -d ex05 -v ON_ERROR_STOP=1 < exercises/05-queries/exercise/queries.sql
-- Um filme pode ter várias categorias: nas perguntas por categoria conta em cada uma.

-- 1. Número de filmes por categoria, incluindo categorias sem filmes, mais filmes primeiro, depois por nome
SELECT c.name AS category, count(fc.film_id) AS films
FROM category c
LEFT JOIN film_category fc ON fc.category_id = c.category_id
GROUP BY c.category_id, c.name
ORDER BY films DESC, c.name;

-- 2. Receita por categoria por mês em 2025, por payment_date
SELECT c.name AS category, date_trunc('month', p.payment_date)::date AS month, sum(p.amount) AS revenue
FROM payment p
JOIN rental r         ON r.rental_id = p.rental_id
JOIN inventory i      ON i.inventory_id = r.inventory_id
JOIN film_category fc ON fc.film_id = i.film_id
JOIN category c       ON c.category_id = fc.category_id
WHERE p.payment_date >= '2025-01-01' AND p.payment_date < '2026-01-01'
GROUP BY c.name, month
ORDER BY c.name, month;

-- 3. Filmes que nunca foram alugados, incluindo filmes sem nenhuma cópia
SELECT f.film_id, f.title
FROM film f
WHERE NOT EXISTS (
    SELECT 1 FROM inventory i JOIN rental r ON r.inventory_id = i.inventory_id
    WHERE i.film_id = f.film_id
)
ORDER BY f.film_id;

-- 4. Clientes que alugaram filmes das 5 classificações
SELECT r.customer_id, c.first_name, c.last_name
FROM rental r
JOIN inventory i ON i.inventory_id = r.inventory_id
JOIN film f      ON f.film_id = i.film_id
JOIN customer c  ON c.customer_id = r.customer_id
GROUP BY r.customer_id, c.first_name, c.last_name
HAVING count(DISTINCT f.rating) = (SELECT count(DISTINCT rating) FROM film)
ORDER BY r.customer_id;

-- 5. Pares de atores que entraram juntos em mais de 3 filmes, cada par uma vez (self join)
SELECT a1.actor_id AS actor_1, a1.first_name || ' ' || a1.last_name AS name_1,
       a2.actor_id AS actor_2, a2.first_name || ' ' || a2.last_name AS name_2,
       count(*) AS films
FROM film_actor fa1
JOIN film_actor fa2 ON fa2.film_id = fa1.film_id AND fa2.actor_id > fa1.actor_id
JOIN actor a1 ON a1.actor_id = fa1.actor_id
JOIN actor a2 ON a2.actor_id = fa2.actor_id
GROUP BY a1.actor_id, a2.actor_id
HAVING count(*) > 3
ORDER BY films DESC, actor_1, actor_2;

-- 6. Países com mais de 20 clientes: nº de clientes e total pago, mais clientes primeiro
-- (os pagamentos são somados antes do join, para não contar cada cliente várias vezes)
WITH customer_paid AS (
    SELECT customer_id, sum(amount) AS paid FROM payment GROUP BY customer_id
)
SELECT co.country, count(*) AS customers, coalesce(sum(cp.paid), 0) AS total_paid
FROM customer cu
JOIN address a  ON a.address_id = cu.address_id
JOIN city ci    ON ci.city_id = a.city_id
JOIN country co ON co.country_id = ci.country_id
LEFT JOIN customer_paid cp ON cp.customer_id = cu.customer_id
GROUP BY co.country
HAVING count(*) > 20
ORDER BY customers DESC, co.country;

-- 7. Clientes que pagaram mais do que o cliente médio do seu país (sem pagamentos = 0)
WITH customer_paid AS (
    SELECT cu.customer_id, cu.first_name, cu.last_name, ci.country_id,
           coalesce((SELECT sum(p.amount) FROM payment p WHERE p.customer_id = cu.customer_id), 0) AS paid
    FROM customer cu
    JOIN address a ON a.address_id = cu.address_id
    JOIN city ci   ON ci.city_id = a.city_id
),
country_avg AS (
    SELECT country_id, avg(paid) AS avg_paid FROM customer_paid GROUP BY country_id
)
SELECT cp.customer_id, cp.first_name, cp.last_name, co.country, cp.paid, round(ca.avg_paid, 2) AS country_avg
FROM customer_paid cp
JOIN country_avg ca ON ca.country_id = cp.country_id
JOIN country co     ON co.country_id = cp.country_id
WHERE cp.paid > ca.avg_paid
ORDER BY co.country, cp.paid DESC, cp.customer_id;

-- 8. Os filmes mais longos de cada classificação, com empates (subquery)
SELECT f.rating, f.film_id, f.title, f.length
FROM film f
WHERE f.length = (SELECT max(f2.length) FROM film f2 WHERE f2.rating = f.rating)
ORDER BY f.rating, f.title;

-- 9. Clientes sem nenhum aluguer a partir de 2026-04-01
SELECT c.customer_id, c.first_name, c.last_name
FROM customer c
WHERE NOT EXISTS (
    SELECT 1 FROM rental r WHERE r.customer_id = c.customer_id AND r.rental_date >= '2026-04-01'
)
ORDER BY c.customer_id;

-- 10. Por categoria, a média de dias que um filme fica fora (só alugueres devolvidos), maior primeiro
SELECT c.name AS category,
       round(avg(extract(epoch FROM r.return_date - r.rental_date) / 86400)::numeric, 2) AS avg_days_out
FROM rental r
JOIN inventory i      ON i.inventory_id = r.inventory_id
JOIN film_category fc ON fc.film_id = i.film_id
JOIN category c       ON c.category_id = fc.category_id
WHERE r.return_date IS NOT NULL
GROUP BY c.name
ORDER BY avg_days_out DESC, c.name;
