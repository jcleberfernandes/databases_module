# Exercício 09 — Segurança

```bash
./scripts/create-db.sh ex09 --pagila
```

## 1. Roles em PostgreSQL

Ficheiros: `roles.sql` (cria `migrations`, `app`, `readonly` e as permissões) e `roles_test.sql` (provas).

```bash
docker compose exec -T postgres psql -U postgres -d ex09 -v ON_ERROR_STOP=1 < exercises/09-security/exercise/roles.sql
docker compose exec -T postgres psql -U postgres -d ex09 < exercises/09-security/exercise/roles_test.sql
```

| Role | Permissões |
|---|---|
| `migrations` | dono da base, `CREATE` no schema (cria/altera/apaga tabelas) |
| `app` | `SELECT, INSERT, UPDATE, DELETE` nas tabelas, `USAGE` nas sequências |
| `readonly` | só `SELECT` |

Resultado:

```
--- app: DROP TABLE tem de falhar
 current_user
--------------
 app
ERROR:  must be owner of table film

--- readonly: SELECT funciona
 current_user
--------------
 readonly
 films
-------
  1000

--- readonly: INSERT tem de falhar
ERROR:  permission denied for table actor
```

## 2. SQL injection na mini-API

Pasta `vulnerable-api/` (FastAPI):
- `main_vulnerable.py` — a versão original, vulnerável.
- `main.py` — a versão corrigida.

```bash
cd exercises/09-security/exercise/vulnerable-api
uv run uvicorn main_vulnerable:app --port 8009     # ou main:app para a versão corrigida
```

Código vulnerável — o texto do utilizador é colado no SQL:

```python
conn.execute(f"SELECT customer_id, first_name, last_name, email FROM customer WHERE email = '{email}'")
```

**Payload 1** — devolve todos os clientes:

```bash
curl -G localhost:8009/customers --data-urlencode "email=' OR '1'='1"
```

O SQL fica `... WHERE email = '' OR '1'='1'`, que é sempre verdadeiro → **999 clientes**.

**Payload 2** — lê outra tabela (utilizadores e hashes das passwords dos funcionários):

```bash
curl -G localhost:8009/customers --data-urlencode "email=' UNION SELECT staff_id, username, password, email FROM staff --"
```

```
[{"id":849,"first_name":"ozzie.friesen","last_name":"8cb2237d0679ca88db6464eac60da96345513964","email":"dietrich7954@mohrandsons.com"}, ...]
```

→ **1500 linhas** da tabela `staff`.

**Correção** — o email é enviado como parâmetro, separado do SQL:

```python
conn.execute(
    "SELECT customer_id, first_name, last_name, email FROM customer WHERE email = %s",
    (email,),
)
```

Com `main.py` o pedido normal continua a funcionar e os dois payloads devolvem `[]`
(o PostgreSQL procura um email que é literalmente `' OR '1'='1`):

```
normal:  [{"id":1,"first_name":"MARY","last_name":"SMITH","email":"MARY.SMITH@sakilacustomer.org"}]
OR 1=1:  []
UNION:   []
```

## 3. Utilizador Redis com ACL

Ficheiro: `redis_acl.sh`.

```bash
bash exercises/09-security/exercise/redis_acl.sh
```

```
> ACL SETUSER app reset on >*** ~* +get +set
OK
> ACL DRYRUN app FLUSHALL   (pergunta ao Redis sem executar)
User app has no permissions to run the 'flushall' command
> [app] SET ex09:x 1
OK
> [app] GET ex09:x
1
> [app] FLUSHALL
NOPERM User app has no permissions to run the 'flushall' command
```

`reset` tira todas as permissões, `~*` dá acesso a todas as chaves e `+get +set`
só deixa correr esses dois comandos. O `ACL DRYRUN` confirma antes que o
`FLUSHALL` vai ser recusado, para nunca correr o risco de apagar o Redis.
