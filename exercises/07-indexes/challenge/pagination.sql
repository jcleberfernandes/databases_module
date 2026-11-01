-- Challenge 07: OFFSET vs keyset, INCLUDE e VACUUM
-- Correr depois de ../exercise/create_big_rental.sql (base ex07)

-- Página 5000 com 20 linhas = linhas 99 981 a 100 000. Os clientes de big_rental
-- têm ~3 300 alugueres cada, por isso criamos o cliente 9999 com 200 000.
DELETE FROM big_rental WHERE customer_id = 9999;
SELECT setseed(0.2);
INSERT INTO big_rental
SELECT 2000000 + g, 9999, now() - random() * interval '3 years', now()
FROM generate_series(1, 200000) AS g;

-- Começar sem os índices do exercício
DROP INDEX IF EXISTS big_rental_customer_rented, big_rental_id, big_rental_open, big_rental_rented,
                      big_rental_keyset, big_rental_keyset_cover;
CREATE INDEX big_rental_keyset ON big_rental (customer_id, rented_at DESC, id DESC);
VACUUM ANALYZE big_rental;

\echo '===== OFFSET: página 5000 ====='
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM big_rental
WHERE customer_id = 9999
ORDER BY rented_at DESC, id DESC
OFFSET 99980 LIMIT 20;

-- Último registo da página 4999 (é o que a aplicação guardaria da página anterior)
SELECT rented_at AS last_rented_at, id AS last_id
FROM big_rental WHERE customer_id = 9999
ORDER BY rented_at DESC, id DESC
OFFSET 99979 LIMIT 1 \gset

\echo '===== KEYSET: página 5000 ====='
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM big_rental
WHERE customer_id = 9999 AND (rented_at, id) < (:'last_rented_at', :last_id)
ORDER BY rented_at DESC, id DESC
LIMIT 20;

\echo '===== As duas dão as mesmas 20 linhas? (0 = sim) ====='
SELECT count(*) AS differences FROM (
    (SELECT * FROM big_rental WHERE customer_id = 9999 ORDER BY rented_at DESC, id DESC OFFSET 99980 LIMIT 20)
    EXCEPT
    (SELECT * FROM big_rental WHERE customer_id = 9999 AND (rented_at, id) < (:'last_rented_at', :last_id)
     ORDER BY rented_at DESC, id DESC LIMIT 20)
) d;

\echo '===== KEYSET com INCLUDE: Index Only Scan ====='
-- SELECT * precisa de returned_at, que não está no índice; com INCLUDE fica lá também.
DROP INDEX big_rental_keyset;
CREATE INDEX big_rental_keyset_cover ON big_rental (customer_id, rented_at DESC, id DESC) INCLUDE (returned_at);
VACUUM ANALYZE big_rental;
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM big_rental
WHERE customer_id = 9999 AND (rented_at, id) < (:'last_rented_at', :last_id)
ORDER BY rented_at DESC, id DESC
LIMIT 20;

\echo '===== Heap Fetches depois de um UPDATE (sem VACUUM) ====='
-- O UPDATE cria versões novas das linhas: as páginas deixam de estar marcadas
-- como "all-visible" no visibility map.
ALTER TABLE big_rental SET (autovacuum_enabled = false);
UPDATE big_rental SET returned_at = now() WHERE customer_id = 9999;
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM big_rental
WHERE customer_id = 9999 AND (rented_at, id) < (:'last_rented_at', :last_id)
ORDER BY rented_at DESC, id DESC
LIMIT 20;

\echo '===== Heap Fetches depois do VACUUM ====='
VACUUM big_rental;
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM big_rental
WHERE customer_id = 9999 AND (rented_at, id) < (:'last_rented_at', :last_id)
ORDER BY rented_at DESC, id DESC
LIMIT 20;
ALTER TABLE big_rental RESET (autovacuum_enabled);
