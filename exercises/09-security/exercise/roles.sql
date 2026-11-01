-- Exercício 09.1: três roles em Pagila (base ex09, cópia de Pagila), como superuser
-- Os roles são do servidor inteiro: se já existirem, o CREATE dá erro e é ignorado.
-- As passwords definem-se à parte, no psql: \password app

DO $$ BEGIN CREATE ROLE migrations LOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE ROLE app LOGIN;        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE ROLE readonly LOGIN;   EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- migrations: dono da base, pode criar e alterar tabelas
ALTER DATABASE ex09 OWNER TO migrations;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO migrations;

-- app: só lê e escreve dados (não é dono de nada, não pode fazer DROP)
GRANT USAGE ON SCHEMA public TO app, readonly;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO app;

-- readonly: só lê
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly;

-- Tabelas que migrations criar no futuro recebem as mesmas permissões
ALTER DEFAULT PRIVILEGES FOR ROLE migrations IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app;
ALTER DEFAULT PRIVILEGES FOR ROLE migrations IN SCHEMA public GRANT USAGE ON SEQUENCES TO app;
ALTER DEFAULT PRIVILEGES FOR ROLE migrations IN SCHEMA public GRANT SELECT ON TABLES TO readonly;
