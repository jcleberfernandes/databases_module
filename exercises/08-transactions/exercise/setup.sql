-- Exercício 08: correr uma vez em ex08 (SQL do enunciado)
ALTER TABLE customer ADD COLUMN balance numeric(10,2) NOT NULL DEFAULT 100 CHECK (balance >= 0);

INSERT INTO staff (first_name, last_name, address_id, store_id, username)
SELECT 'Temp', 'Staff ' || g, 1, 1, 'temp' || g
FROM generate_series(1, 14) AS g;
