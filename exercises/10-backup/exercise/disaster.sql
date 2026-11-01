-- Simulação do script do formador: apaga dados de 3 tabelas
DELETE FROM payment WHERE payment_date < '2023-01-01';
DELETE FROM film_actor WHERE actor_id <= 50;
DELETE FROM film_category WHERE category_id IN (1, 2, 3);
