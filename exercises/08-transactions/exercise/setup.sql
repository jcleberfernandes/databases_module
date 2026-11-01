-- Exercício 08: preparação (base ex08, cópia de Pagila)
-- Saldo nos clientes para o lost update
ALTER TABLE customer ADD COLUMN IF NOT EXISTS balance numeric NOT NULL DEFAULT 100 CHECK (balance >= 0);
UPDATE customer SET balance = 100 WHERE customer_id IN (1, 2);

-- Write skew: a loja 1 tem 6 funcionários ativos; juntamos 14 para chegar a 20
INSERT INTO staff (first_name, last_name, address_id, store_id, active, username)
SELECT 'Extra', 'Staff ' || g, 1, 1, true, 'extra' || g
FROM generate_series(1, 20 - (SELECT count(*) FROM staff WHERE store_id = 1 AND active)) AS g;

SELECT count(*) AS active_store_1 FROM staff WHERE store_id = 1 AND active;
