-- Challenge 07: OFFSET vs keyset, INCLUDE e VACUUM
-- ./scripts/create-db.sh ch07 --reset
-- docker compose exec -T postgres psql -U postgres -d ch07 -v ON_ERROR_STOP=1 < exercises/07-indexes/exercise/setup.sql
-- docker compose exec -T postgres psql -U postgres -d ch07 -v ON_ERROR_STOP=1 < exercises/07-indexes/challenge/pagination.sql
-- Páginas de 20 linhas da tabela inteira por rented_at DESC, id DESC. A página 5 000 começa depois de 99 980 linhas.

-- 1. Índice com a mesma ordem da paginação
CREATE INDEX big_rental_page ON big_rental (rented_at DESC, id DESC);

\echo '===== 2. OFFSET: página 5000'
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, rented_at, customer_id FROM big_rental
ORDER BY rented_at DESC, id DESC OFFSET 99980 LIMIT 20;

\echo '===== 3. Keyset: página 5000'
-- a última linha da página 4 999 (a aplicação guardava-a da página anterior)
SELECT rented_at AS last_rented_at, id AS last_id
FROM big_rental ORDER BY rented_at DESC, id DESC OFFSET 99979 LIMIT 1 \gset

EXPLAIN (ANALYZE, BUFFERS)
SELECT id, rented_at, customer_id FROM big_rental
WHERE (rented_at, id) < (:'last_rented_at', :last_id)
ORDER BY rented_at DESC, id DESC LIMIT 20;

\echo '===== 3. As duas devolvem as mesmas 20 linhas? (0 diferenças = sim)'
SELECT count(*) AS differences FROM (
    (SELECT id, rented_at, customer_id FROM big_rental ORDER BY rented_at DESC, id DESC OFFSET 99980 LIMIT 20)
    EXCEPT
    (SELECT id, rented_at, customer_id FROM big_rental
     WHERE (rented_at, id) < (:'last_rented_at', :last_id) ORDER BY rented_at DESC, id DESC LIMIT 20)
) d;

\echo '===== 3. Keyset numa página muito mais à frente (50 000): o tempo não depende da página'
SELECT rented_at AS deep_rented_at, id AS deep_id
FROM big_rental ORDER BY rented_at DESC, id DESC OFFSET 999979 LIMIT 1 \gset
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, rented_at, customer_id FROM big_rental
WHERE (rented_at, id) < (:'deep_rented_at', :deep_id)
ORDER BY rented_at DESC, id DESC LIMIT 20;
\echo '===== 3. ... e o OFFSET na mesma página 50 000'
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, rented_at, customer_id FROM big_rental
ORDER BY rented_at DESC, id DESC OFFSET 999980 LIMIT 20;

\echo '===== 4. Índice com INCLUDE (customer_id): Index Only Scan'
DROP INDEX big_rental_page;
CREATE INDEX big_rental_page ON big_rental (rented_at DESC, id DESC) INCLUDE (customer_id);
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, rented_at, customer_id FROM big_rental
WHERE (rented_at, id) < (:'last_rented_at', :last_id)
ORDER BY rented_at DESC, id DESC LIMIT 20;

\echo '===== 5. Depois do UPDATE (sem VACUUM)'
UPDATE big_rental SET customer_id = customer_id WHERE id % 50 = 0;
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, rented_at, customer_id FROM big_rental
WHERE (rented_at, id) < (:'last_rented_at', :last_id)
ORDER BY rented_at DESC, id DESC LIMIT 20;

\echo '===== 5. Depois do VACUUM'
VACUUM big_rental;
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, rented_at, customer_id FROM big_rental
WHERE (rented_at, id) < (:'last_rented_at', :last_id)
ORDER BY rented_at DESC, id DESC LIMIT 20;
