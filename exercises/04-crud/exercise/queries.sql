-- Exercício 04: CRUD, upsert e transações em Pagila (correr por esta ordem, numa cópia nova)
-- ./scripts/create-db.sh ex04 --pagila --reset
-- docker compose exec -T postgres psql -U postgres -d ex04 -v ON_ERROR_STOP=1 < exercises/04-crud/exercise/queries.sql

-- 1. Filmes PG-13 com mais de 120 minutos, por título
SELECT title, length FROM film
WHERE rating = 'PG-13' AND length > 120
ORDER BY title;

-- 2. Atores cujo apelido contém "son", em maiúsculas ou minúsculas
SELECT actor_id, first_name, last_name FROM actor
WHERE last_name ILIKE '%son%'
ORDER BY last_name, first_name;

-- 3. Alugueres ainda não devolvidos
SELECT rental_id, rental_date, customer_id FROM rental
WHERE return_date IS NULL
ORDER BY rental_id;

-- 4. Valores distintos de rental_duration
SELECT DISTINCT rental_duration FROM film ORDER BY rental_duration;

-- 5. Terceira página de filmes por título, 10 por página
SELECT film_id, title FROM film
ORDER BY title
LIMIT 10 OFFSET 20;

-- 6. Alugueres de janeiro de 2026, de duas formas
-- BETWEEN '2026-01-01' AND '2026-01-31' compara com 2026-01-31 00:00:00: deixa de fora tudo o
-- que foi alugado no dia 31 depois da meia-noite. A segunda forma (>= dia 1 e < dia 1 do mês
-- seguinte) apanha o mês inteiro, qualquer que seja a hora: é a correta.
SELECT count(*) AS with_between FROM rental
WHERE rental_date BETWEEN '2026-01-01' AND '2026-01-31';
SELECT count(*) AS with_half_open_range FROM rental
WHERE rental_date >= '2026-01-01' AND rental_date < '2026-02-01';

-- 7. Inserir o ator ADA LOVELACE e devolver o actor_id gerado
INSERT INTO actor (first_name, last_name) VALUES ('ADA', 'LOVELACE')
RETURNING actor_id;

-- 8. Subir 0.50 o rental_rate dos filmes NC-17 com menos de 60 minutos, numa transação
BEGIN;
SELECT count(*) FROM film WHERE rating = 'NC-17' AND length < 60;
UPDATE film SET rental_rate = rental_rate + 0.50
WHERE rating = 'NC-17' AND length < 60
RETURNING film_id, title, rental_rate;
COMMIT;

-- 9. Upsert: mais um prémio para o ator 1 (corrido duas vezes)
CREATE TABLE actor_award (
    actor_id integer PRIMARY KEY REFERENCES actor,
    awards   integer NOT NULL DEFAULT 0
);
INSERT INTO actor_award (actor_id, awards) VALUES (1, 1)
ON CONFLICT (actor_id) DO UPDATE SET awards = actor_award.awards + 1
RETURNING actor_id, awards;
INSERT INTO actor_award (actor_id, awards) VALUES (1, 1)
ON CONFLICT (actor_id) DO UPDATE SET awards = actor_award.awards + 1
RETURNING actor_id, awards;

-- 10. Ator 2 com 5 prémios, ON CONFLICT DO NOTHING (corrido duas vezes)
INSERT INTO actor_award (actor_id, awards) VALUES (2, 5) ON CONFLICT DO NOTHING;
INSERT INTO actor_award (actor_id, awards) VALUES (2, 5) ON CONFLICT DO NOTHING;

-- 11. Três pagamentos de teste numa só instrução
INSERT INTO payment (customer_id, staff_id, rental_id, amount, payment_date)
VALUES (1, 2, 76, 0.01, '2026-07-30 12:00+00'),
       (1, 2, 76, 0.01, '2026-07-30 12:00+00'),
       (1, 2, 76, 0.01, '2026-07-30 12:00+00')
RETURNING payment_id;

-- 12. Apagar os três pagamentos de teste, verificando o WHERE primeiro, numa transação
BEGIN;
SELECT count(*) FROM payment
WHERE customer_id = 1 AND rental_id = 76 AND amount = 0.01 AND payment_date = '2026-07-30 12:00+00';
DELETE FROM payment
WHERE customer_id = 1 AND rental_id = 76 AND amount = 0.01 AND payment_date = '2026-07-30 12:00+00'
RETURNING payment_id;
COMMIT;
