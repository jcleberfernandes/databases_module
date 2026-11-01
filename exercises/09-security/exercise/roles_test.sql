-- Exercício 09.1: provas (correr sem ON_ERROR_STOP, os erros são esperados)

\echo '--- app: DROP TABLE tem de falhar'
SET ROLE app;
SELECT current_user;
DROP TABLE film;
RESET ROLE;

\echo '--- readonly: SELECT funciona'
SET ROLE readonly;
SELECT current_user;
SELECT count(*) AS films FROM film;

\echo '--- readonly: INSERT tem de falhar'
INSERT INTO actor (first_name, last_name) VALUES ('X', 'Y');
RESET ROLE;
