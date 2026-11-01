-- Exercício 04: 12 operações CRUD em Pagila
-- ./scripts/create-db.sh ex04 --pagila
-- docker compose exec -T postgres psql -U postgres -d ex04 -v ON_ERROR_STOP=1 < exercises/04-crud/exercise/queries.sql
-- (o resultado esperado está no comentário de cada operação)

-- 1. Filmes PG-13 com mais de 120 minutos, por título
-- Esperado: 118 linhas
SELECT title, length FROM film
WHERE rating = 'PG-13' AND length > 120
ORDER BY title;

-- 2. Clientes sem alugueres no último ano (último ano = 365 dias antes do último aluguer)
-- Esperado: 2 linhas
SELECT c.customer_id, c.first_name, c.last_name
FROM customer c
WHERE NOT EXISTS (
    SELECT 1 FROM rental r
    WHERE r.customer_id = c.customer_id
      AND r.rental_date > (SELECT max(rental_date) FROM rental) - interval '1 year'
)
ORDER BY c.customer_id;

-- 3. Quantos filmes há em cada classificação
-- Esperado: 5 linhas (G 178, PG 194, PG-13 223, R 195, NC-17 210)
SELECT rating, count(*) FROM film GROUP BY rating ORDER BY rating;

-- 4. Os 10 filmes mais longos
-- Esperado: 10 linhas, a primeira CHICAGO NORTH com length 185
SELECT title, length FROM film ORDER BY length DESC, title LIMIT 10;

-- 5. Inserir um ator e devolver o id gerado
-- Esperado: 1 linha (actor_id 201)
INSERT INTO actor (first_name, last_name) VALUES ('ADA', 'LOVELACE')
RETURNING actor_id, first_name, last_name;

-- 6. Atualizar o preço de aluguer da categoria Horror com RETURNING
-- Esperado: 142 linhas, todas com rental_rate 1.99
UPDATE film f SET rental_rate = 1.99
FROM film_category fc JOIN category c ON c.category_id = fc.category_id
WHERE fc.film_id = f.film_id AND c.name = 'Horror'
RETURNING f.film_id, f.title, f.rental_rate;

-- 7. Upsert de um ator com id fixo (corre 2 vezes: 1.º insere, 2.º atualiza)
-- Esperado: 1 linha cada vez; no fim actor 500 chama-se GRACE HOPPER
INSERT INTO actor (actor_id, first_name, last_name) OVERRIDING SYSTEM VALUE
VALUES (500, 'GRACE', 'HOPPER')
ON CONFLICT (actor_id) DO UPDATE SET first_name = EXCLUDED.first_name, last_name = EXCLUDED.last_name
RETURNING actor_id, first_name, last_name;
INSERT INTO actor (actor_id, first_name, last_name) OVERRIDING SYSTEM VALUE
VALUES (500, 'GRACE', 'HOPPER')
ON CONFLICT (actor_id) DO UPDATE SET first_name = EXCLUDED.first_name, last_name = EXCLUDED.last_name
RETURNING actor_id, first_name, last_name;

-- 8. Upsert numa tabela de contagem de visualizações
-- Esperado: views = 2 na segunda execução
CREATE TABLE IF NOT EXISTS film_views (
    film_id int PRIMARY KEY REFERENCES film,
    views   int NOT NULL DEFAULT 0
);
INSERT INTO film_views VALUES (1, 1)
ON CONFLICT (film_id) DO UPDATE SET views = film_views.views + 1 RETURNING *;
INSERT INTO film_views VALUES (1, 1)
ON CONFLICT (film_id) DO UPDATE SET views = film_views.views + 1 RETURNING *;

-- 9. Criar 3 pagamentos de teste (amount 0) para depois apagar
-- Esperado: 3 linhas
INSERT INTO payment (customer_id, staff_id, rental_id, amount, payment_date)
VALUES (1, 1, 1, 0, '2026-07-01'), (2, 1, 2, 0, '2026-07-01'), (3, 1, 3, 0, '2026-07-01')
RETURNING payment_id, amount;

-- 10. Apagar os pagamentos de teste, verificando o WHERE primeiro
-- Esperado: o SELECT dá 3 e o DELETE apaga 3
BEGIN;
SELECT count(*) FROM payment WHERE amount = 0 AND payment_date = '2026-07-01';
DELETE FROM payment WHERE amount = 0 AND payment_date = '2026-07-01'
RETURNING payment_id;
COMMIT;

-- 11. Clientes inativos (active = 0)
-- Esperado: 44 linhas
SELECT customer_id, first_name, last_name FROM customer WHERE activebool = false OR active = 0
ORDER BY customer_id;

-- 12. Atores com apelido começado por 'S'
-- Esperado: 9 linhas
SELECT actor_id, first_name, last_name FROM actor
WHERE last_name LIKE 'S%'
ORDER BY last_name, first_name;
