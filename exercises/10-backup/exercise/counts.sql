-- Contagens usadas para verificar a recuperação
SELECT (SELECT count(*) FROM payment)       AS payment,
       (SELECT count(*) FROM film_actor)    AS film_actor,
       (SELECT count(*) FROM film_category) AS film_category,
       (SELECT count(*) FROM rental)        AS rental;
