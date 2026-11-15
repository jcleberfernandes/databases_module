#!/usr/bin/env bash
# Backup da base pagila: pagila_YYYY-MM-DD_HHMM.dump (formato custom) e, ao lado,
# pagila_YYYY-MM-DD_HHMM.counts com o nº de linhas de cada tabela no momento do dump.
# Depois aplica a retenção: fica o último backup de cada um dos últimos 7 dias e o último
# de cada uma das últimas 4 semanas; o resto é apagado.
# Uso (na raiz do repositório ou em qualquer sítio):
#   bash exercises/10-backup/challenge/backup.sh                    # hoje
#   bash exercises/10-backup/challenge/backup.sh --now 2026-10-01   # finge que hoje é 2026-10-01
set -euo pipefail
cd "$(dirname "$0")/../../.."            # raiz do repositório (onde está o docker-compose.yml)

NOW=$(date +%F)
if [ "${1:-}" = "--now" ]; then NOW="$2"; fi
DIR=backups/pagila
mkdir -p "$DIR"
NAME="$DIR/pagila_${NOW}_$(date +%H%M)"

# Contagem exata de cada tabela (query_to_xml corre um count(*) por tabela)
COUNTS="SELECT table_name, (xpath('/row/c/text()',
          query_to_xml(format('SELECT count(*) AS c FROM public.%I', table_name), false, true, '')))[1]::text
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name"

# As contagens e o dump na mesma transação (snapshot) seria o ideal; aqui o pagila não muda
# durante o backup, por isso contam-se logo antes do dump.
docker compose exec -T postgres psql -U postgres -d pagila -XtA -F ' ' -c "$COUNTS" > "$NAME.counts.tmp"
docker compose exec -T postgres pg_dump -U postgres -Fc pagila > "$NAME.dump.tmp"
mv "$NAME.dump.tmp" "$NAME.dump"; mv "$NAME.counts.tmp" "$NAME.counts"   # só fica se tudo correu bem
echo "$(date '+%F %T') backup $NAME.dump ($(du -h "$NAME.dump" | cut -f1), $(wc -l < "$NAME.counts") tabelas)"

# ---- retenção
keep=()
for i in 0 1 2 3 4 5 6; do                       # o último de cada um dos últimos 7 dias
    day=$(date -d "$NOW -$i day" +%F)
    last=$(ls -1 "$DIR"/pagila_"${day}"_*.dump 2>/dev/null | tail -1 || true)
    [ -n "$last" ] && keep+=("$last")
done
for i in 0 1 2 3; do                             # o último de cada uma das últimas 4 semanas (ISO)
    week=$(date -d "$NOW -$((7 * i)) day" +%G-W%V)
    last=""
    for f in "$DIR"/pagila_*.dump; do
        d=$(basename "$f" | cut -d_ -f2)
        [ "$(date -d "$d" +%G-W%V)" = "$week" ] && last="$f"
    done
    [ -n "$last" ] && keep+=("$last")
done
for f in "$DIR"/pagila_*.dump; do
    if ! printf '%s\n' "${keep[@]}" | grep -qx "$f"; then
        rm "$f" "${f%.dump}.counts"
        echo "$(date '+%F %T') apagado $f"
    fi
done
