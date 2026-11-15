#!/usr/bin/env bash
# Restaura o dump mais recente de backups/pagila num contentor descartável, conta as linhas de
# todas as tabelas e compara com o .counts desse dump. Mostra as diferenças e sai com 1 se houver.
# Uso:  bash exercises/10-backup/challenge/verify.sh
set -euo pipefail
cd "$(dirname "$0")/../../.."

LATEST=$(ls -1 backups/pagila/pagila_*.dump | tail -1)       # os nomes ordenam por data
COUNTS_FILE="${LATEST%.dump}.counts"
NAME="pg-verify-$$"
echo "$(date '+%F %T') verificar $LATEST"

COUNTS="SELECT table_name, (xpath('/row/c/text()',
          query_to_xml(format('SELECT count(*) AS c FROM public.%I', table_name), false, true, '')))[1]::text
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name"

docker run --rm -d --name "$NAME" -e POSTGRES_PASSWORD=verify postgres:18 > /dev/null
trap 'docker stop "$NAME" > /dev/null' EXIT                 # o contentor é apagado sempre no fim
until docker exec "$NAME" pg_isready -U postgres -q; do sleep 1; done
sleep 2                                                     # o arranque reinicia o servidor uma vez
until docker exec "$NAME" pg_isready -U postgres -q; do sleep 1; done

docker exec "$NAME" createdb -U postgres pagila
docker exec -i "$NAME" pg_restore -U postgres -d pagila --no-owner < "$LATEST"
TMP=$(mktemp)
docker exec -i "$NAME" psql -U postgres -d pagila -XtA -F ' ' -c "$COUNTS" > "$TMP"

if diff "$COUNTS_FILE" "$TMP" > "$TMP.diff"; then
    echo "$(date '+%F %T') OK: as $(wc -l < "$TMP") tabelas têm as contagens do .counts"
    STATUS=0
else
    echo "$(date '+%F %T') ERRO: contagens diferentes (< .counts, > restaurado):"
    cat "$TMP.diff"
    STATUS=1
fi
rm -f "$TMP" "$TMP.diff"
exit $STATUS
