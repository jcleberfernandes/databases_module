-- Challenge 09: provas. Corre COM LOGIN COMO app (não como superuser), sem ON_ERROR_STOP:
--   docker compose exec -T postgres psql -U app -d ex09 < exercises/09-security/challenge/rls_test.sql

\echo '--- ligado como:'
SELECT current_user, session_user;


\echo '--- app sem app.customer_id: não vê nada'
SELECT count(*) AS rentals FROM rental;

\echo '--- app com app.customer_id = 42: query SEM WHERE'
SET app.customer_id = '42';
SELECT count(*) AS rentals, count(DISTINCT customer_id) AS customers, min(customer_id), max(customer_id) FROM rental;
SELECT count(*) AS payments, count(DISTINCT customer_id) AS customers, min(customer_id), max(customer_id) FROM payment;

\echo '--- tentativa 1: pedir outro cliente no WHERE'
SELECT count(*) FROM rental WHERE customer_id = 1;

\echo '--- tentativa 2: desligar o RLS na sessão'
SET row_security = off;
SELECT count(*) FROM rental;
RESET row_security;

\echo '--- tentativa 3: desligar o RLS na tabela'
ALTER TABLE rental DISABLE ROW LEVEL SECURITY;

\echo '--- tentativa 4: ler uma partição de payment diretamente'
SELECT count(*) FROM payment_p2022_01;

\echo '--- tentativa 5: inserir um aluguer de outro cliente'
INSERT INTO rental (rental_date, inventory_id, customer_id, staff_id) VALUES (now(), 1, 1, 1);

\echo '--- tentativa 6: passar a superuser'
SET ROLE postgres;

\echo '--- o app não tem BYPASSRLS nem é dono das tabelas'
SELECT rolname, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = 'app';
SELECT tableowner FROM pg_tables WHERE tablename = 'rental';
