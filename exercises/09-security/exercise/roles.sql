-- Exercício 09, tarefa 1: roles em ex09 (correr como postgres)
-- As passwords vêm de variáveis de ambiente, passadas ao psql com -v (ver README):
--   psql -v migrations_password=... -v app_password=... -v readonly_password=...

-- Os roles são do servidor inteiro: só se criam se ainda não existirem
SELECT 'CREATE ROLE ex09_migrations LOGIN' WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ex09_migrations') \gexec
SELECT 'CREATE ROLE ex09_app LOGIN'        WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ex09_app') \gexec
SELECT 'CREATE ROLE ex09_readonly LOGIN'   WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ex09_readonly') \gexec
ALTER ROLE ex09_migrations PASSWORD :'migrations_password';
ALTER ROLE ex09_app        PASSWORD :'app_password';
ALTER ROLE ex09_readonly   PASSWORD :'readonly_password';

-- ex09_migrations é o dono da base (cria e altera tabelas)
ALTER DATABASE ex09 OWNER TO ex09_migrations;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
-- o schema public do Pagila é do postgres: ser dono da base não chega para criar tabelas nele
GRANT USAGE, CREATE ON SCHEMA public TO ex09_migrations;
GRANT USAGE ON SCHEMA public TO ex09_app, ex09_readonly;

-- ex09_app: lê e escreve dados, mais nada
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ex09_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO ex09_app;

-- ex09_readonly: só lê
GRANT SELECT ON ALL TABLES IN SCHEMA public TO ex09_readonly;

-- tabelas (e sequências) que ex09_migrations criar mais tarde recebem as mesmas permissões
ALTER DEFAULT PRIVILEGES FOR ROLE ex09_migrations IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ex09_app;
ALTER DEFAULT PRIVILEGES FOR ROLE ex09_migrations IN SCHEMA public
    GRANT USAGE ON SEQUENCES TO ex09_app;
ALTER DEFAULT PRIVILEGES FOR ROLE ex09_migrations IN SCHEMA public
    GRANT SELECT ON TABLES TO ex09_readonly;
