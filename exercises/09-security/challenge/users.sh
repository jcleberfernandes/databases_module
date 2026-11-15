#!/usr/bin/env bash
# Utilizadores só de leitura da instância B (o ex09_readonly do PostgreSQL já existe, do exercício).
# Também deixa o ex09_app do Redis ler os contadores (GET), para os GET funcionarem na instância A.
# As passwords vêm do .env.b desta pasta; as de administrador são as que os contentores já têm.
# Uso (na raiz do repositório):  bash exercises/09-security/challenge/users.sh
set -euo pipefail
cd "$(dirname "$0")/../../.."
set -a; source exercises/09-security/challenge/.env.b; set +a

echo "== MongoDB: ex09_reader (role read em ex09)"
docker compose exec -T -e PW="$MONGO_READER_PASSWORD" mongo sh -c \
  'mongosh -u "$MONGO_INITDB_ROOT_USERNAME" -p "$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase admin --quiet ex09 --eval "
     if (db.getUser(\"ex09_reader\")) db.dropUser(\"ex09_reader\");
     db.createUser({user: \"ex09_reader\", pwd: process.env.PW, roles: [{role: \"read\", db: \"ex09\"}]});
     print(\"ex09_reader criado\")"'

echo "== Redis: ex09_reader (só GET em counter:*) e +get para ex09_app"
docker compose exec -T -e PW="$REDIS_READER_PASSWORD" redis sh -c \
  'redis-cli -a "$REDIS_PASSWORD" --no-auth-warning ACL SETUSER ex09_reader reset on ">$PW" "~counter:*" +get &&
   redis-cli -a "$REDIS_PASSWORD" --no-auth-warning ACL SETUSER ex09_app +get'
