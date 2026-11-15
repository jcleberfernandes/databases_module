#!/usr/bin/env bash
# Restaura o backup mais recente de pagila_docs para a base pagila_docs_restored
# e mostra o nº de documentos de cada coleção nas duas bases.
# Uso (na raiz do repositório):  bash exercises/14-pipelines/exercise/restore_mongo.sh
set -euo pipefail
cd "$(dirname "$0")/../../.."
LATEST=$(ls -1t backups/mongo_pagila_docs_*.archive.gz | head -1)
echo "restaurar: $LATEST -> pagila_docs_restored"

docker compose exec -T mongo sh -c \
  'mongorestore -u "$MONGO_INITDB_ROOT_USERNAME" -p "$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase admin --archive --gzip --drop --nsFrom "pagila_docs.*" --nsTo "pagila_docs_restored.*" --quiet' \
  < "$LATEST"

COUNTS='
const a = db.getSiblingDB("pagila_docs"), b = db.getSiblingDB("pagila_docs_restored");
let ok = true;
print("coleção".padEnd(16), "pagila_docs".padStart(12), "restored".padStart(12));
a.getCollectionNames().sort().forEach(c => {
  const x = a[c].countDocuments(), y = b[c].countDocuments();
  ok = ok && x === y;
  print(c.padEnd(16), String(x).padStart(12), String(y).padStart(12), x === y ? "OK" : "DIFERENTE");
});
print(ok ? "todas as coleções têm o mesmo nº de documentos" : "HÁ DIFERENÇAS");
'
docker compose exec -T mongo sh -c \
  'mongosh -u "$MONGO_INITDB_ROOT_USERNAME" -p "$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase admin --quiet --eval "$1"' \
  -- "$COUNTS"
