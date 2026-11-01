-- Atividade normal da loja DEPOIS do backup (para medir o que se perde = RPO real)
INSERT INTO film_actor (actor_id, film_id)
SELECT 1, f FROM generate_series(990, 994) AS f
WHERE NOT EXISTS (SELECT 1 FROM film_actor WHERE actor_id = 1 AND film_id = f);
INSERT INTO payment (customer_id, staff_id, rental_id, amount, payment_date)
VALUES (1, 1, 1, 9.99, '2022-12-31 10:00'), (2, 1, 2, 4.99, '2026-07-28 12:00');
