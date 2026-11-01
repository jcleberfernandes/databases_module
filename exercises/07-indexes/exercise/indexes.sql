-- Exercício 07: 5 queries, plano antes, índice, plano depois
-- Correr depois de create_big_rental.sql

\echo '===== Q1: últimos 10 alugueres de um cliente ====='
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM big_rental WHERE customer_id = 42 ORDER BY rented_at DESC LIMIT 10;
CREATE INDEX big_rental_customer_rented ON big_rental (customer_id, rented_at DESC);
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM big_rental WHERE customer_id = 42 ORDER BY rented_at DESC LIMIT 10;

\echo '===== Q2: um aluguer pelo id ====='
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM big_rental WHERE id = 1234567;
CREATE UNIQUE INDEX big_rental_id ON big_rental (id);
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM big_rental WHERE id = 1234567;

\echo '===== Q3: alugueres por devolver há mais de 30 dias ====='
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*) FROM big_rental WHERE returned_at IS NULL AND rented_at < now() - interval '30 days';
CREATE INDEX big_rental_open ON big_rental (rented_at) WHERE returned_at IS NULL;
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*) FROM big_rental WHERE returned_at IS NULL AND rented_at < now() - interval '30 days';

\echo '===== Q4: alugueres de um único dia ====='
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM big_rental WHERE rented_at >= now() - interval '100 days' AND rented_at < now() - interval '99 days';
CREATE INDEX big_rental_rented ON big_rental (rented_at);
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM big_rental WHERE rented_at >= now() - interval '100 days' AND rented_at < now() - interval '99 days';

\echo '===== Q5: alugueres dos últimos 2 anos (o índice NÃO ajuda) ====='
-- O índice big_rental_rented (de Q4) já existe e o planner não o usa.
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM big_rental WHERE rented_at > now() - interval '730 days';
-- Forçar o índice para provar que é mais lento:
SET enable_seqscan = off;
SET enable_bitmapscan = off;
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM big_rental WHERE rented_at > now() - interval '730 days';
RESET enable_seqscan;
RESET enable_bitmapscan;
