#!/usr/bin/env bash
# Restaura o backup mais recente num contentor descartável e compara as contagens
# de linhas de todas as tabelas com a base em produção. Sai com código 1 se houver diferenças.
# Uso:  bash exercises/10-backup/challenge/verify.sh [base]
set -euo pipefail
cd "$(dirname "$0")/../../.."

DB="${1:-ex10}"
LATEST=$(ls -1t "backups/$DB"/daily/*.dump | head -1)
NAME="pg-verify-$$"
echo "$(date '+%F %T') verificar $LATEST"

# Contagem exata de cada tabela do schema public (query_to_xml corre um count(*) por tabela)
COUNTS="SELECT table_name, (xpath('/row/c/text()',
          query_to_xml(format('SELECT count(*) AS c FROM public.%I', table_name), false, true, '')))[1]::text
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name"

docker run --rm -d --name "$NAME" -e POSTGRES_PASSWORD=verify postgres:18 > /dev/null
trap 'docker stop "$NAME" > /dev/null' EXIT        # o contentor é sempre apagado no fim
until docker exec "$NAME" pg_isready -U postgres -q; do sleep 1; done
sleep 2                                            # o arranque do contentor reinicia o servidor uma vez
until docker exec "$NAME" pg_isready -U postgres -q; do sleep 1; done

docker exec "$NAME" createdb -U postgres "$DB"
docker exec -i "$NAME" pg_restore -U postgres -d "$DB" --no-owner < "$LATEST"

docker exec -i "$NAME" psql -U postgres -d "$DB" -tA -F' ' -c "$COUNTS" > /tmp/verify_backup_$$.txt
docker compose exec -T postgres psql -U postgres -d "$DB" -tA -F' ' -c "$COUNTS" > /tmp/verify_live_$$.txt

if diff /tmp/verify_backup_$$.txt /tmp/verify_live_$$.txt > /tmp/verify_diff_$$.txt; then
    echo "$(date '+%F %T') OK: $(wc -l < /tmp/verify_live_$$.txt) tabelas com as mesmas contagens"
    STATUS=0
else
    echo "$(date '+%F %T') ERRO: contagens diferentes (< backup, > produção):"
    cat /tmp/verify_diff_$$.txt
    STATUS=1
fi
rm -f /tmp/verify_*_$$.txt
exit $STATUS
