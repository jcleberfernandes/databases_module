#!/usr/bin/env bash
# Backup de pagila_docs para backups/ num arquivo comprimido com data no nome.
# Uso (na raiz do repositório):  bash exercises/14-pipelines/exercise/backup_mongo.sh
set -euo pipefail
cd "$(dirname "$0")/../../.."
mkdir -p backups
FILE="backups/mongo_pagila_docs_$(date +%F_%H%M%S).archive.gz"
# mongodump corre no contentor, com o utilizador e a password que o contentor já tem
docker compose exec -T mongo sh -c \
  'mongodump -u "$MONGO_INITDB_ROOT_USERNAME" -p "$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase admin --db pagila_docs --archive --gzip' \
  > "$FILE.tmp"
mv "$FILE.tmp" "$FILE"     # só fica com o nome final se o dump terminou bem
echo "backup: $FILE ($(du -h "$FILE" | cut -f1))"
