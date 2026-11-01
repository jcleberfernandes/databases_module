#!/usr/bin/env bash
# Backup da base ex10 em formato custom, com nome com data/hora,
# e retenção de 7 backups diários e 4 semanais.
# Uso:  bash exercises/10-backup/challenge/backup.sh [base]
set -euo pipefail
cd "$(dirname "$0")/../../.."          # raiz do repositório (onde está o docker-compose.yml)

DB="${1:-ex10}"
DIR="backups/$DB"
mkdir -p "$DIR/daily" "$DIR/weekly"

FILE="$DIR/daily/${DB}_$(date +%F_%H%M%S).dump"
docker compose exec -T postgres pg_dump -U postgres -Fc "$DB" > "$FILE.tmp"
mv "$FILE.tmp" "$FILE"                 # só fica com o nome final se o dump terminou bem
echo "$(date '+%F %T') backup $FILE ($(du -h "$FILE" | cut -f1))"

# Semanal: o primeiro backup de cada semana (ano + nº da semana ISO) é copiado para weekly/
WEEKLY="$DIR/weekly/${DB}_$(date +%G-W%V).dump"
if [ ! -f "$WEEKLY" ]; then
    cp "$FILE" "$WEEKLY"
    echo "$(date '+%F %T') semanal $WEEKLY"
fi

# Retenção: fica com os 7 diários e os 4 semanais mais recentes
ls -1t "$DIR"/daily/*.dump  | tail -n +8 | xargs -r rm -v
ls -1t "$DIR"/weekly/*.dump | tail -n +5 | xargs -r rm -v
