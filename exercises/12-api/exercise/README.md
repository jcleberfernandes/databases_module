# Exercício 12 — Migrações e API transacional

Ficheiros:
- `app/models.py` — `customer`, `film`, `inventory`, `rental`, `staff`.
- `app/db.py` — engine (com `echo=True`) e uma sessão por pedido.
- `app/main.py` — os 3 endpoints.
- `alembic.ini`, `migrations/env.py` (com `include_object`), `migrations/versions/0001…0003`.
- `concurrency_test.py`, `pyproject.toml`, `.env.example`.

A ligação vem de `DATABASE_URL` (ver `.env.example`; copiar para `.env`). Sem `.env`, o
`app/db.py` usa o `POSTGRES_USER`/`POSTGRES_PASSWORD` do `.env` da raiz.

## Como correr

```bash
./scripts/create-db.sh ex12 --pagila --reset
cd exercises/12-api/exercise
uv sync
uv run alembic stamp 0001          # baseline: a base já tem o schema do Pagila
uv run alembic upgrade head        # 0002 e 0003
uv run uvicorn app.main:app        # API em http://127.0.0.1:8000/docs
# noutro terminal, na mesma pasta:
uv run python concurrency_test.py
```

(O passo 1 do enunciado diz `alembic stamp head`: quando o fiz só existia a `0001`, por isso
`head` era a `0001`. Agora que existem 3 migrações, numa cópia nova tem de ser `stamp 0001`;
`stamp head` marcaria a 0002 e a 0003 como feitas sem as correr.)

## 1. Baseline e `include_object`

`0001_baseline.py` tem `upgrade` e `downgrade` vazios. `alembic stamp` só escreve a versão na
tabela `alembic_version`, sem executar nada.

`include_object` em `migrations/env.py` ignora tudo o que existe na base mas não nos modelos:

```python
def include_object(obj, name, type_, reflected, compare_to):
    if reflected and compare_to is None:
        return False
    return True
```

**O que o `--autogenerate` teria gerado.** Medi com `compare_metadata` na base `ex12`:

| Situação | Operações propostas |
|---|---|
| sem baseline (projeto sem modelos ainda) | `drop_table` × 70 e `drop_index` × 91 — apagar o Pagila inteiro |
| com os 5 modelos mas sem `include_object` | `drop_table` × 65, `drop_index` × 91, `drop_column` × 27 (as colunas não mapeadas, ex: `customer.address_id`), `drop_fk` × 11 |

O autogenerate compara os modelos com a base: o que está na base e não está nos modelos é
"para apagar". O Pagila tem ~20 tabelas mais 55 partições de `payment` e nós só mapeamos 5,
com algumas colunas. Sem o filtro, um `alembic upgrade` desse ficheiro apagava tabelas e
colunas com dados reais — e ninguém repara se não ler o ficheiro gerado.

Depois de ajustar os tipos dos modelos aos do Pagila (`Text`, `SmallInteger`,
`DateTime(timezone=True)`, FKs com `ON UPDATE CASCADE ON DELETE RESTRICT`), `alembic check` diz:

```
No new upgrade operations detected.
```

## 2. `0002_loyalty_points`

```python
op.add_column("customer", sa.Column("loyalty_points", sa.Integer(), nullable=True))   # 1. nullable
op.execute("UPDATE customer c SET loyalty_points = (SELECT count(*) FROM rental r WHERE r.customer_id = c.customer_id)")  # 2. preencher
op.alter_column("customer", "loyalty_points", nullable=False, server_default=sa.text("0"))  # 3. NOT NULL
```

```
 customer_id | loyalty_points
-------------+----------------
           1 |             66
```

## 3. `0003_one_open_rental_per_copy`

Fecha o aluguer aberto mais antigo de cada cópia com a `rental_date` do mais recente
(com `row_number()` e `first_value()` por `inventory_id`), e cria o índice
`rental_one_open_per_copy ON rental (inventory_id) WHERE return_date IS NULL`.
Depois da migração não há cópias com dois alugueres abertos (`0 rows`).

**Porque o `downgrade` não desfaz a correção dos dados.** Os dados antigos estavam errados
(uma cópia física não pode estar alugada a duas pessoas ao mesmo tempo). Desfazer seria voltar
a pôr dados inválidos. Além disso, depois da migração a aplicação continua a trabalhar: essas
linhas podem ter sido alteradas outra vez, e o downgrade já não consegue saber quais
`return_date` eram nossos. O `downgrade` só remove o índice, que é a parte estrutural.

## 4. upgrade → downgrade → upgrade

```
################ alembic upgrade head
INFO  [alembic.runtime.migration] Running upgrade 0001 -> 0002, customer.loyalty_points em três passos
INFO  [alembic.runtime.migration] Running upgrade 0002 -> 0003, no máximo um aluguer aberto por cópia
                                             Table "public.customer"
     Column     |           Type           | Collation | Nullable |                    Default                    
----------------+--------------------------+-----------+----------+-----------------------------------------------
 customer_id    | integer                  |           | not null | nextval('customer_customer_id_seq'::regclass)
 store_id       | integer                  |           | not null | 
 first_name     | text                     |           | not null | 
 last_name      | text                     |           | not null | 
 email          | text                     |           |          | 
 address_id     | integer                  |           | not null | 
 activebool     | boolean                  |           | not null | true
 create_date    | date                     |           | not null | CURRENT_DATE
 last_update    | timestamp with time zone |           |          | now()
 active         | integer                  |           |          | 
 uuid           | uuid                     |           | not null | uuidv7()
 loyalty_points | integer                  |           | not null | 0
Indexes:
    "customer_pkey" PRIMARY KEY, btree (customer_id)
    "customer_uuid_key" UNIQUE, btree (uuid)
    "idx_fk_address_id" btree (address_id)
    "idx_fk_store_id" btree (store_id)
    "idx_last_name" btree (last_name)
Foreign-key constraints:
    "customer_address_id_fkey" FOREIGN KEY (address_id) REFERENCES address(address_id) ON UPDATE CASCADE ON DELETE RESTRICT
    "customer_store_id_fkey" FOREIGN KEY (store_id) REFERENCES store(store_id) ON UPDATE CASCADE ON DELETE RESTRICT
    TABLE "rental" CONSTRAINT "rental_customer_id_fkey" FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON UPDATE CASCADE ON DELETE RESTRICT
Triggers:
    last_updated BEFORE UPDATE ON customer FOR EACH ROW EXECUTE FUNCTION last_updated()

                                           Table "public.rental"
    Column    |           Type           | Collation | Nullable |                  Default                  
--------------+--------------------------+-----------+----------+-------------------------------------------
 rental_id    | integer                  |           | not null | nextval('rental_rental_id_seq'::regclass)
 rental_date  | timestamp with time zone |           | not null | 
 inventory_id | integer                  |           | not null | 
 customer_id  | integer                  |           | not null | 
 return_date  | timestamp with time zone |           |          | 
 staff_id     | integer                  |           | not null | 
 last_update  | timestamp with time zone |           | not null | now()
 uuid         | uuid                     |           | not null | uuidv7()
Indexes:
    "rental_pkey" PRIMARY KEY, btree (rental_id)
    "idx_fk_inventory_id" btree (inventory_id)
    "idx_unq_rental_rental_date_inventory_id_customer_id" UNIQUE, btree (rental_date, inventory_id, customer_id)
    "rental_one_open_per_copy" UNIQUE, btree (inventory_id) WHERE return_date IS NULL
    "rental_uuid_key" UNIQUE, btree (uuid)
Foreign-key constraints:
    "rental_customer_id_fkey" FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON UPDATE CASCADE ON DELETE RESTRICT
    "rental_inventory_id_fkey" FOREIGN KEY (inventory_id) REFERENCES inventory(inventory_id) ON UPDATE CASCADE ON DELETE RESTRICT
    "rental_staff_id_fkey" FOREIGN KEY (staff_id) REFERENCES staff(staff_id) ON UPDATE CASCADE ON DELETE RESTRICT
Triggers:
    last_updated BEFORE UPDATE ON rental FOR EACH ROW EXECUTE FUNCTION last_updated()

################ alembic downgrade base
INFO  [alembic.runtime.migration] Running downgrade 0003 -> 0002, no máximo um aluguer aberto por cópia
INFO  [alembic.runtime.migration] Running downgrade 0002 -> 0001, customer.loyalty_points em três passos
INFO  [alembic.runtime.migration] Running downgrade 0001 -> , baseline: o schema do Pagila tal como já existe
                                            Table "public.customer"
   Column    |           Type           | Collation | Nullable |                    Default                    
-------------+--------------------------+-----------+----------+-----------------------------------------------
 customer_id | integer                  |           | not null | nextval('customer_customer_id_seq'::regclass)
 store_id    | integer                  |           | not null | 
 first_name  | text                     |           | not null | 
 last_name   | text                     |           | not null | 
 email       | text                     |           |          | 
 address_id  | integer                  |           | not null | 
 activebool  | boolean                  |           | not null | true
 create_date | date                     |           | not null | CURRENT_DATE
 last_update | timestamp with time zone |           |          | now()
 active      | integer                  |           |          | 
 uuid        | uuid                     |           | not null | uuidv7()
Indexes:
    "customer_pkey" PRIMARY KEY, btree (customer_id)
    "customer_uuid_key" UNIQUE, btree (uuid)
    "idx_fk_address_id" btree (address_id)
    "idx_fk_store_id" btree (store_id)
    "idx_last_name" btree (last_name)
Foreign-key constraints:
    "customer_address_id_fkey" FOREIGN KEY (address_id) REFERENCES address(address_id) ON UPDATE CASCADE ON DELETE RESTRICT
    "customer_store_id_fkey" FOREIGN KEY (store_id) REFERENCES store(store_id) ON UPDATE CASCADE ON DELETE RESTRICT
    TABLE "rental" CONSTRAINT "rental_customer_id_fkey" FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON UPDATE CASCADE ON DELETE RESTRICT
Triggers:
    last_updated BEFORE UPDATE ON customer FOR EACH ROW EXECUTE FUNCTION last_updated()

                                           Table "public.rental"
    Column    |           Type           | Collation | Nullable |                  Default                  
--------------+--------------------------+-----------+----------+-------------------------------------------
 rental_id    | integer                  |           | not null | nextval('rental_rental_id_seq'::regclass)
 rental_date  | timestamp with time zone |           | not null | 
 inventory_id | integer                  |           | not null | 
 customer_id  | integer                  |           | not null | 
 return_date  | timestamp with time zone |           |          | 
 staff_id     | integer                  |           | not null | 
 last_update  | timestamp with time zone |           | not null | now()
 uuid         | uuid                     |           | not null | uuidv7()
Indexes:
    "rental_pkey" PRIMARY KEY, btree (rental_id)
    "idx_fk_inventory_id" btree (inventory_id)
    "idx_unq_rental_rental_date_inventory_id_customer_id" UNIQUE, btree (rental_date, inventory_id, customer_id)
    "rental_uuid_key" UNIQUE, btree (uuid)
Foreign-key constraints:
    "rental_customer_id_fkey" FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON UPDATE CASCADE ON DELETE RESTRICT
    "rental_inventory_id_fkey" FOREIGN KEY (inventory_id) REFERENCES inventory(inventory_id) ON UPDATE CASCADE ON DELETE RESTRICT
    "rental_staff_id_fkey" FOREIGN KEY (staff_id) REFERENCES staff(staff_id) ON UPDATE CASCADE ON DELETE RESTRICT
Triggers:
    last_updated BEFORE UPDATE ON rental FOR EACH ROW EXECUTE FUNCTION last_updated()

################ alembic upgrade head
INFO  [alembic.runtime.migration] Running upgrade  -> 0001, baseline: o schema do Pagila tal como já existe
INFO  [alembic.runtime.migration] Running upgrade 0001 -> 0002, customer.loyalty_points em três passos
INFO  [alembic.runtime.migration] Running upgrade 0002 -> 0003, no máximo um aluguer aberto por cópia
                                             Table "public.customer"
     Column     |           Type           | Collation | Nullable |                    Default                    
----------------+--------------------------+-----------+----------+-----------------------------------------------
 customer_id    | integer                  |           | not null | nextval('customer_customer_id_seq'::regclass)
 store_id       | integer                  |           | not null | 
 first_name     | text                     |           | not null | 
 last_name      | text                     |           | not null | 
 email          | text                     |           |          | 
 address_id     | integer                  |           | not null | 
 activebool     | boolean                  |           | not null | true
 create_date    | date                     |           | not null | CURRENT_DATE
 last_update    | timestamp with time zone |           |          | now()
 active         | integer                  |           |          | 
 uuid           | uuid                     |           | not null | uuidv7()
 loyalty_points | integer                  |           | not null | 0
Indexes:
    "customer_pkey" PRIMARY KEY, btree (customer_id)
    "customer_uuid_key" UNIQUE, btree (uuid)
    "idx_fk_address_id" btree (address_id)
    "idx_fk_store_id" btree (store_id)
    "idx_last_name" btree (last_name)
Foreign-key constraints:
    "customer_address_id_fkey" FOREIGN KEY (address_id) REFERENCES address(address_id) ON UPDATE CASCADE ON DELETE RESTRICT
    "customer_store_id_fkey" FOREIGN KEY (store_id) REFERENCES store(store_id) ON UPDATE CASCADE ON DELETE RESTRICT
    TABLE "rental" CONSTRAINT "rental_customer_id_fkey" FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON UPDATE CASCADE ON DELETE RESTRICT
Triggers:
    last_updated BEFORE UPDATE ON customer FOR EACH ROW EXECUTE FUNCTION last_updated()

                                           Table "public.rental"
    Column    |           Type           | Collation | Nullable |                  Default                  
--------------+--------------------------+-----------+----------+-------------------------------------------
 rental_id    | integer                  |           | not null | nextval('rental_rental_id_seq'::regclass)
 rental_date  | timestamp with time zone |           | not null | 
 inventory_id | integer                  |           | not null | 
 customer_id  | integer                  |           | not null | 
 return_date  | timestamp with time zone |           |          | 
 staff_id     | integer                  |           | not null | 
 last_update  | timestamp with time zone |           | not null | now()
 uuid         | uuid                     |           | not null | uuidv7()
Indexes:
    "rental_pkey" PRIMARY KEY, btree (rental_id)
    "idx_fk_inventory_id" btree (inventory_id)
    "idx_unq_rental_rental_date_inventory_id_customer_id" UNIQUE, btree (rental_date, inventory_id, customer_id)
    "rental_one_open_per_copy" UNIQUE, btree (inventory_id) WHERE return_date IS NULL
    "rental_uuid_key" UNIQUE, btree (uuid)
Foreign-key constraints:
    "rental_customer_id_fkey" FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON UPDATE CASCADE ON DELETE RESTRICT
    "rental_inventory_id_fkey" FOREIGN KEY (inventory_id) REFERENCES inventory(inventory_id) ON UPDATE CASCADE ON DELETE RESTRICT
    "rental_staff_id_fkey" FOREIGN KEY (staff_id) REFERENCES staff(staff_id) ON UPDATE CASCADE ON DELETE RESTRICT
Triggers:
    last_updated BEFORE UPDATE ON rental FOR EACH ROW EXECUTE FUNCTION last_updated()

```

## 5. API

| Endpoint | Respostas |
|---|---|
| `POST /rentals` | `201` `{rental_id, inventory_id}`, `404` cliente/filme não existe, `409` sem cópia livre |
| `POST /rentals/{rental_id}/return` | `200`, `404` não existe, `409` já devolvido |
| `GET /rentals/overdue?as_of=2026-07-31` | lista de alugueres em atraso |

`POST /rentals`: numa transação procura uma cópia do filme na loja sem aluguer aberto, com
`with_for_update(skip_locked=True)`, e insere o aluguer. Se o INSERT violar
`rental_one_open_per_copy` (outro pedido alugou a mesma cópia entre a leitura e o INSERT),
apanha o `IntegrityError` e repete a transação inteira, no máximo 3 vezes, antes de dar `409`.

Testes manuais (cópia nova, depois do `concurrency_test.py`):

```
cliente inexistente: 404
filme inexistente: 404
{"rental_id":87561,"return_date":"2026-11-04T20:43:12.876105+00:00"} -> 200
{"detail":"Rental already returned"} -> 409
{"detail":"Rental not found"} -> 404
{"rental_id":87562,"inventory_id":32} -> 201      (a cópia devolvida volta a estar livre)
```

`GET /rentals/overdue?as_of=2026-07-31` devolve **229 itens**:

```json
{
  "rental_id": 11496,
  "rental_date": "2022-02-14T15:16:03+00:00",
  "due_date": "2022-02-19T15:16:03+00:00",
  "customer": {"customer_id": 155, "first_name": "GAIL", "last_name": "KNIGHT"},
  "film": {"film_id": 445, "title": "HYDE DOCTOR"}
}
```

**Nº de SQL no log do `echo=True`: 1 `SELECT`** (entre o `BEGIN (implicit)` e o `ROLLBACK`).
O cliente, a cópia e o filme vêm na mesma query com `joinedload`, por isso não há N+1:

```
INFO sqlalchemy.engine.Engine SELECT rental.rental_id, rental.rental_date, ..., rental.rental_date
  + make_interval(..., film.rental_duration) AS due_date, customer_1.customer_id AS customer_id_1, ...,
  film_1.film_id, film_1.title, ... FROM rental JOIN inventory ... JOIN film ...
  LEFT OUTER JOIN customer AS customer_1 ... LEFT OUTER JOIN inventory AS inventory_1 ...
  WHERE rental.return_date IS NULL AND ... < %(param_1)s ORDER BY rental.rental_date, rental.rental_id
```

## 6. `concurrency_test.py`

Três execuções, cada uma numa cópia nova com as migrações:

```
== execução 1
cliente 1: 409 {'detail': 'No copy available'}
cliente 2: 201 {'rental_id': 87561, 'inventory_id': 32}
cliente 3: 409 {'detail': 'No copy available'}
cliente 4: 409 {'detail': 'No copy available'}
cliente 5: 201 {'rental_id': 87560, 'inventory_id': 33}
201: 2  409: 3  inventory_id diferentes: [32, 33]
OK
== execução 2
cliente 1: 201 {'rental_id': 87561, 'inventory_id': 33}
cliente 2: 409 {'detail': 'No copy available'}
cliente 3: 409 {'detail': 'No copy available'}
cliente 4: 409 {'detail': 'No copy available'}
cliente 5: 201 {'rental_id': 87560, 'inventory_id': 32}
201: 2  409: 3  inventory_id diferentes: [32, 33]
OK
== execução 3
cliente 1: 409 {'detail': 'No copy available'}
cliente 2: 409 {'detail': 'No copy available'}
cliente 3: 201 {'rental_id': 87561, 'inventory_id': 32}
cliente 4: 409 {'detail': 'No copy available'}
cliente 5: 201 {'rental_id': 87560, 'inventory_id': 33}
201: 2  409: 3  inventory_id diferentes: [32, 33]
OK
```

Quem ganha muda de execução para execução, mas o resultado é sempre 2 × `201` (cópias 32 e 33) e 3 × `409`.
