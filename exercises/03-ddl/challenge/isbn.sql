-- Challenge 03: DOMAIN isbn13 (correr depois de ../exercise/schema.sql)

-- Valida formato (13 dígitos, hífens opcionais) e o dígito de controlo.
-- Regra do ISBN-13: pesos 1,3,1,3,... nos 12 primeiros dígitos;
-- o 13.º dígito = (10 - soma % 10) % 10
CREATE OR REPLACE FUNCTION is_valid_isbn13(value text) RETURNS boolean
LANGUAGE sql IMMUTABLE AS $$
    SELECT value ~ '^[0-9-]+$'
       AND length(replace(value, '-', '')) = 13
       AND (
           SELECT (10 - sum(substr(d, i, 1)::int * CASE WHEN i % 2 = 0 THEN 3 ELSE 1 END) % 10) % 10
           FROM (SELECT replace(value, '-', '') AS d) x, generate_series(1, 12) AS i
           GROUP BY d
       ) = substr(replace(value, '-', ''), 13, 1)::int
$$;

DROP DOMAIN IF EXISTS isbn13 CASCADE;
CREATE DOMAIN isbn13 AS text CHECK (is_valid_isbn13(VALUE));

ALTER TABLE book ALTER COLUMN isbn TYPE isbn13;

-- Válido: aceite
INSERT INTO book (isbn, title, year, publisher_id) VALUES ('978-0-306-40615-7', 'ISBN válido', 2000, 1);
SELECT isbn, title FROM book WHERE title = 'ISBN válido';

-- Dígito de controlo errado (…6 em vez de …7): rejeitado
INSERT INTO book (isbn, title, year, publisher_id) VALUES ('978-0-306-40615-6', 'ISBN errado', 2000, 1);
