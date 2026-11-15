#!/usr/bin/env bash
# Cria os roles do PostgreSQL (roles.sql), o utilizador do MongoDB e o utilizador ACL do Redis.
# As passwords vêm do .env desta pasta. As credenciais de administrador são as que os
# contentores já têm (nunca aparecem aqui).
# Uso (na raiz do repositório):  bash exercises/09-security/exercise/users.sh
set -euo pipefail
cd "$(dirname "$0")/../../.."
set -a; source exercises/09-security/exercise/.env; set +a

echo "== PostgreSQL: roles.sql"
docker compose exec -T postgres psql -U postgres -d ex09 -v ON_ERROR_STOP=1 \
  -v migrations_password="$EX09_MIGRATIONS_PASSWORD" -v app_password="$EX09_APP_PASSWORD" \
  -v readonly_password="$EX09_READONLY_PASSWORD" < exercises/09-security/exercise/roles.sql

echo "== MongoDB: utilizador ex09_app (readWrite em ex09)"
docker compose exec -T -e PW="$MONGO_APP_PASSWORD" mongo sh -c \
  'mongosh -u "$MONGO_INITDB_ROOT_USERNAME" -p "$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase admin --quiet ex09 --eval "
     if (db.getUser(\"ex09_app\")) db.dropUser(\"ex09_app\");
     db.createUser({user: \"ex09_app\", pwd: process.env.PW, roles: [{role: \"readWrite\", db: \"ex09\"}]});
     print(\"ex09_app criado\")"'

echo "== Redis: utilizador ACL ex09_app (só INCR em counter:*)"
docker compose exec -T -e PW="$REDIS_APP_PASSWORD" redis sh -c \
  'redis-cli -a "$REDIS_PASSWORD" --no-auth-warning ACL SETUSER ex09_app reset on ">$PW" "~counter:*" +incr'
