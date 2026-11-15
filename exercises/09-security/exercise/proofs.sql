-- Exercício 09, tarefa 2: provas (correr como postgres, depois de roles.sql)
-- docker compose exec -T postgres psql -U postgres -d ex09 < exercises/09-security/exercise/proofs.sql

SET ROLE ex09_app;
-- Esperado: FALHA (ERROR: must be owner of table film)
DROP TABLE film;
-- Esperado: FUNCIONA (INSERT 0 1)
INSERT INTO actor (first_name, last_name) VALUES ('X', 'Y');
RESET ROLE;

SET ROLE ex09_readonly;
-- Esperado: FUNCIONA (1000)
SELECT count(*) FROM film;
-- Esperado: FALHA (ERROR: permission denied for table actor)
INSERT INTO actor (first_name, last_name) VALUES ('X', 'Y');
RESET ROLE;
