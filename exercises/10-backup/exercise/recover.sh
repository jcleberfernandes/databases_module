#!/usr/bin/env bash
# Recupera payment, film_actor e film_category da base ex10 a partir de um dump.
# Uso (na raiz do repositório):  bash exercises/10-backup/exercise/recover.sh backups/ex10_XXXX.dump
set -euo pipefail
DUMP="${1:?indica o ficheiro .dump}"
psql() { docker compose exec -T postgres psql -U postgres -v ON_ERROR_STOP=1 -q "$@"; }

echo "1. restaurar o dump numa base separada (ex10_restored)"
psql -d postgres -c "DROP DATABASE IF EXISTS ex10_restored WITH (FORCE)"
psql -d postgres -c "CREATE DATABASE ex10_restored"
docker compose exec -T postgres pg_restore -U postgres -d ex10_restored --no-owner < "$DUMP"

echo "2. copiar as 3 tabelas do backup para um schema temporário em ex10"
psql -d ex10 -c "DROP SCHEMA IF EXISTS recovery CASCADE; CREATE SCHEMA recovery;"
for t in payment film_actor film_category; do
    psql -d ex10 -c "CREATE TABLE recovery.$t (LIKE public.$t)"
    psql -d ex10_restored -c "COPY (SELECT * FROM public.$t) TO STDOUT" | psql -d ex10 -c "COPY recovery.$t FROM STDIN"
done

echo "3. voltar a inserir só as linhas que faltam (as que existem ficam como estão)"
psql -d ex10 <<'SQL'
BEGIN;
INSERT INTO public.payment       SELECT * FROM recovery.payment       ON CONFLICT DO NOTHING;
INSERT INTO public.film_actor    SELECT * FROM recovery.film_actor    ON CONFLICT DO NOTHING;
INSERT INTO public.film_category SELECT * FROM recovery.film_category ON CONFLICT DO NOTHING;
COMMIT;
DROP SCHEMA recovery CASCADE;
SQL

echo "4. limpar"
psql -d postgres -c "DROP DATABASE ex10_restored WITH (FORCE)"
echo "feito"
