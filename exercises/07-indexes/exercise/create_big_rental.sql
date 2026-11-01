-- Cria a tabela big_rental com 2 milhões de linhas (SQL do tutorial da sessão 07)
DROP TABLE IF EXISTS big_rental;
SELECT setseed(0.1);
CREATE TABLE big_rental AS
SELECT g AS id,
       (random() * 599 + 1)::int                 AS customer_id,
       now() - random() * interval '3 years'      AS rented_at,
       CASE WHEN random() < 0.03 THEN NULL ELSE now() END AS returned_at
FROM generate_series(1, 2000000) AS g;
VACUUM ANALYZE big_rental;
