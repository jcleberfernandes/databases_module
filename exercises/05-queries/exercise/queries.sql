-- Exercício 05: 10 perguntas de negócio em Pagila
-- ./scripts/create-db.sh ex05 --pagila
-- docker compose exec -T postgres psql -U postgres -d ex05 -v ON_ERROR_STOP=1 < exercises/05-queries/exercise/queries.sql

-- 1. Receita por categoria por mês
SELECT c.name AS category,
       date_trunc('month', p.payment_date)::date AS month,
       sum(p.amount) AS revenue
FROM payment p
JOIN rental r         ON r.rental_id = p.rental_id
JOIN inventory i      ON i.inventory_id = r.inventory_id
JOIN film_category fc ON fc.film_id = i.film_id
JOIN category c       ON c.category_id = fc.category_id
GROUP BY c.name, month
ORDER BY month, revenue DESC
LIMIT 20;

-- 2. Top 5 clientes de cada loja (por valor gasto)
WITH spent AS (
    SELECT c.store_id, c.customer_id, c.first_name, c.last_name, sum(p.amount) AS total,
           row_number() OVER (PARTITION BY c.store_id ORDER BY sum(p.amount) DESC, c.customer_id) AS pos
    FROM customer c
    JOIN payment p ON p.customer_id = c.customer_id
    GROUP BY c.customer_id
)
SELECT store_id, pos, customer_id, first_name, last_name, total
FROM spent
WHERE pos <= 5
ORDER BY store_id, pos;

-- 3. Filmes que nunca foram alugados
SELECT f.film_id, f.title
FROM film f
WHERE NOT EXISTS (
    SELECT 1 FROM inventory i JOIN rental r ON r.inventory_id = i.inventory_id
    WHERE i.film_id = f.film_id
)
ORDER BY f.title;

-- 4. Pares de atores que entraram juntos em mais de 3 filmes (self join)
SELECT a1.first_name || ' ' || a1.last_name AS actor_1,
       a2.first_name || ' ' || a2.last_name AS actor_2,
       count(*) AS films
FROM film_actor fa1
JOIN film_actor fa2 ON fa2.film_id = fa1.film_id AND fa2.actor_id > fa1.actor_id
JOIN actor a1 ON a1.actor_id = fa1.actor_id
JOIN actor a2 ON a2.actor_id = fa2.actor_id
GROUP BY a1.actor_id, a2.actor_id
HAVING count(*) > 3
ORDER BY films DESC, actor_1, actor_2;

-- 5. Clientes que gastam mais do que a média da sua cidade
WITH customer_total AS (
    SELECT c.customer_id, c.first_name, c.last_name, a.city_id, sum(p.amount) AS total
    FROM customer c
    JOIN address a ON a.address_id = c.address_id
    JOIN payment p ON p.customer_id = c.customer_id
    GROUP BY c.customer_id, a.city_id
),
city_avg AS (
    SELECT city_id, avg(total) AS avg_total FROM customer_total GROUP BY city_id
)
SELECT ct.customer_id, ct.first_name, ct.last_name, ci.city, ct.total, round(ca.avg_total, 2) AS city_avg
FROM customer_total ct
JOIN city_avg ca ON ca.city_id = ct.city_id
JOIN city ci     ON ci.city_id = ct.city_id
WHERE ct.total > ca.avg_total
ORDER BY ci.city, ct.total DESC;

-- 6. Número de filmes por categoria
SELECT c.name, count(*) AS films
FROM category c
JOIN film_category fc ON fc.category_id = c.category_id
GROUP BY c.name
ORDER BY films DESC, c.name;

-- 7. Os 10 filmes mais alugados
SELECT f.title, count(*) AS rentals
FROM rental r
JOIN inventory i ON i.inventory_id = r.inventory_id
JOIN film f      ON f.film_id = i.film_id
GROUP BY f.film_id
ORDER BY rentals DESC, f.title
LIMIT 10;

-- 8. Alugueres ainda não devolvidos, por cliente (top 10)
SELECT c.customer_id, c.first_name, c.last_name, count(*) AS not_returned
FROM rental r
JOIN customer c ON c.customer_id = r.customer_id
WHERE r.return_date IS NULL
GROUP BY c.customer_id
ORDER BY not_returned DESC, c.customer_id
LIMIT 10;

-- 9. Atores que nunca entraram num filme da categoria Horror (subquery)
SELECT a.actor_id, a.first_name, a.last_name
FROM actor a
WHERE a.actor_id NOT IN (
    SELECT fa.actor_id
    FROM film_actor fa
    JOIN film_category fc ON fc.film_id = fa.film_id
    JOIN category c       ON c.category_id = fc.category_id
    WHERE c.name = 'Horror'
)
ORDER BY a.actor_id;

-- 10. Receita por país (top 10)
SELECT co.country, sum(p.amount) AS revenue
FROM payment p
JOIN customer c ON c.customer_id = p.customer_id
JOIN address a  ON a.address_id = c.address_id
JOIN city ci    ON ci.city_id = a.city_id
JOIN country co ON co.country_id = ci.country_id
GROUP BY co.country
ORDER BY revenue DESC
LIMIT 10;
