#!/usr/bin/env bash
# Exercício 09.3: utilizador Redis "app" que pode GET e SET mas não FLUSHALL.
# Correr da raiz do repositório:  bash exercises/09-security/exercise/redis_acl.sh
# A password do utilizador app vem de REDIS_APP_PASSWORD (por omissão: change-me-app).
set -euo pipefail
APP_PASSWORD="${REDIS_APP_PASSWORD:-change-me-app}"

# Como o utilizador default (admin), dentro do contentor (usa a variável REDIS_PASSWORD do contentor)
admin() { docker compose exec -T redis sh -c 'redis-cli -a "$REDIS_PASSWORD" --no-auth-warning "$@"' -- "$@"; }
# Como o utilizador app
app() { docker compose exec -T redis redis-cli --user app --pass "$APP_PASSWORD" --no-auth-warning "$@"; }

echo "> ACL SETUSER app reset on >*** ~* +get +set"
admin ACL SETUSER app reset on ">$APP_PASSWORD" "~*" +get +set

echo "> ACL DRYRUN app FLUSHALL   (pergunta ao Redis sem executar)"
admin ACL DRYRUN app FLUSHALL

echo "> [app] SET ex09:x 1";    app SET ex09:x 1
echo "> [app] GET ex09:x";      app GET ex09:x
echo "> [app] FLUSHALL";        app FLUSHALL
echo "> [app] DEL ex09:x";      app DEL ex09:x
admin DEL ex09:x > /dev/null
