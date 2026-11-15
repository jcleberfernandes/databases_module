# Challenge 12 — Renomear `customer.email` sem downtime (expand e contract)

Ficheiros:
- `migrations/versions/0004_expand_email_address.py` — expand.
- `migrations/versions/0005_contract_email.py` — contract.
- `api_v1.py` (porta 8001, usa `email`) e `api_v2.py` (porta 8002, usa `email_address`).
- `check_versions.py` — os pedidos do passo 3.
- `alembic.ini`, `migrations/env.py`, `db.py`, `pyproject.toml`, `.env.example`.

As migrações continuam a cadeia do exercício: o `alembic.ini` tem
`version_locations` com `../exercise/migrations/versions` e `./migrations/versions`, por isso
`alembic history` mostra `0001 → 0002 → 0003 → 0004 → 0005`.

## Ordem do deploy

```bash
./scripts/create-db.sh ex12 --pagila --reset
cd exercises/12-api/challenge
uv sync
uv run alembic stamp 0001 && uv run alembic upgrade 0003     # estado do exercício
uv run uvicorn api_v1:app --port 8001 &                      # 1. v1 em produção
uv run alembic upgrade 0004                                  # 2. expand (a v1 continua a funcionar)
uv run uvicorn api_v2:app --port 8002 &                      # 3. v2 ao lado da v1
uv run python check_versions.py                              # 4. as duas veem as mudanças uma da outra
kill %1                                                      # 5. parar a v1 (todo o tráfego na v2)
uv run alembic upgrade 0005                                  # 6. contract
uv run python check_versions.py --only-v2                    # 7. a v2 continua a funcionar
```

Porque nesta ordem: cada passo é compatível com o código que está a correr nesse momento.
O expand só **acrescenta** (a v1 não sabe que `email_address` existe e não se importa).
O trigger mantém as duas colunas iguais enquanto há as duas versões. O contract só **apaga**
`email` quando já ninguém a usa. (A API do exercício usa `email`: depois do contract também tem de estar parada.)

## Expand (0004)

```python
op.add_column("customer", sa.Column("email_address", sa.Text(), nullable=True))
op.execute("UPDATE customer SET email_address = email")          # backfill
op.execute(SYNC_FUNCTION)                                          # função plpgsql
op.execute("CREATE TRIGGER customer_sync_email BEFORE INSERT OR UPDATE ON customer "
           "FOR EACH ROW EXECUTE FUNCTION customer_sync_email()")
```

A função compara `NEW` com `OLD`: se mudou `email`, copia para `email_address`; se mudou
`email_address`, copia para `email`. É um trigger `BEFORE`, que altera a própria linha antes
de ser gravada, por isso não faz um segundo `UPDATE` nem entra em recursão.

## Saída de `check_versions` depois do expand

```
PUT http://127.0.0.1:8001 email=mary.from.v1@example.com -> 200 | GET http://127.0.0.1:8002 -> 200 email=mary.from.v1@example.com OK
PUT http://127.0.0.1:8002 email=mary.from.v2@example.com -> 200 | GET http://127.0.0.1:8001 -> 200 email=mary.from.v2@example.com OK
OK
```

## Contract (0005) e v2 depois do contract

```
INFO  [alembic.runtime.migration] Running upgrade 0004 -> 0005, contract: apagar customer.email (só depois de parar a v1)
colunas email*: email_address          triggers: (nenhum)
```

```
PUT http://127.0.0.1:8002 email=mary.v2.only@example.com -> 200 | GET http://127.0.0.1:8002 -> 200 email=mary.v2.only@example.com OK
v1 parada (como deve estar depois do contract)
OK
{"customer_id":1,"first_name":"MARY","last_name":"SMITH","email":"mary.v2.only@example.com"}
```

`email` já não existe; a v2 continua a funcionar.

## Downgrade de cada migração

```
### downgrade do contract (0005 -> 0004)
INFO  [alembic.runtime.migration] Running downgrade 0005 -> 0004, contract: ...
colunas email*: email_address, email   triggers: customer_sync_email
 customer_id |          email           |      email_address
-------------+--------------------------+--------------------------
           1 | mary.v2.only@example.com | mary.v2.only@example.com

### downgrade do expand (0004 -> 0003)
INFO  [alembic.runtime.migration] Running downgrade 0004 -> 0003, expand: ...
colunas email*: email                  triggers: (nenhum)

### upgrade head outra vez
INFO  [alembic.runtime.migration] Running upgrade 0003 -> 0004, expand: ...
INFO  [alembic.runtime.migration] Running upgrade 0004 -> 0005, contract: ...
colunas email*: email_address          triggers: (nenhum)
```

O downgrade do contract volta a criar `email` preenchida a partir de `email_address` (nada se
perde) e recria o trigger, ficando como depois do expand.
