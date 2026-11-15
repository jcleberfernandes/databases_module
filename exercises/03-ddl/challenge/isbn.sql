-- Challenge 03: DOMAIN isbn13
-- ./scripts/create-db.sh ch03
-- docker compose exec -T postgres psql -U postgres -d ch03 < exercises/03-ddl/challenge/isbn.sql

DROP TABLE IF EXISTS book;
DROP DOMAIN IF EXISTS isbn13;
DROP FUNCTION IF EXISTS is_valid_isbn13(text);

-- Formato: dígitos com hífens só ENTRE dígitos (nunca no início, no fim, nem dois seguidos),
-- e 13 dígitos no total.
-- Dígito de controlo: os 12 primeiros dígitos × 1, 3, 1, 3, ... somados;
-- o 13.º tem de ser (10 - soma % 10) % 10.
CREATE FUNCTION is_valid_isbn13(value text) RETURNS boolean
LANGUAGE sql IMMUTABLE AS $$
    SELECT value ~ '^[0-9](-?[0-9])*$'
       AND length(replace(value, '-', '')) = 13
       AND (10 - (SELECT sum(substr(replace(value, '-', ''), i, 1)::int * CASE WHEN i % 2 = 1 THEN 1 ELSE 3 END)
                  FROM generate_series(1, 12) AS i) % 10) % 10
           = substr(replace(value, '-', ''), 13, 1)::int
$$;

CREATE DOMAIN isbn13 AS text CHECK (is_valid_isbn13(VALUE));

CREATE TABLE book (
    book_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    isbn    isbn13 NOT NULL UNIQUE,
    title   text NOT NULL
);

-- Aceites
INSERT INTO book (isbn, title) VALUES ('978-0-306-40615-7', 'válido 1');
INSERT INTO book (isbn, title) VALUES ('9781402894626', 'válido 2');
INSERT INTO book (isbn, title) VALUES ('978-3-16-148410-0', 'válido 3');

-- Rejeitados
INSERT INTO book (isbn, title) VALUES ('978-0-306-40615-8', 'dígito de controlo errado');
INSERT INTO book (isbn, title) VALUES ('978-0-306-4061', 'curto demais');
INSERT INTO book (isbn, title) VALUES ('-9780306406157', 'hífen no início');
INSERT INTO book (isbn, title) VALUES ('978--0306406157', 'dois hífens seguidos');

SELECT book_id, isbn, title FROM book ORDER BY book_id;
