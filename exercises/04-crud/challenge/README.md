# Challenge 04 — 1 000 000 de alugueres com COPY

Ficheiros: `seed.py`, `checksum.sql` (o checksum do enunciado), `pyproject.toml`, `.env.example`.

## Como correr

```bash
./scripts/create-db.sh ch04_a --pagila --reset
./scripts/create-db.sh ch04_b --pagila --reset
cd exercises/04-crud/challenge
time uv run python seed.py ch04_a
time uv run python seed.py ch04_b
cd ../../..
docker compose exec -T postgres psql -U postgres -d ch04_a < exercises/04-crud/challenge/checksum.sql
docker compose exec -T postgres psql -U postgres -d ch04_b < exercises/04-crud/challenge/checksum.sql
```

O nome da base é o argumento. A ligação vem de `POSTGRES_URL` (ver `.env.example`); sem `.env`,
usa a password do `.env` da raiz.

## Como o `seed.py` cumpre as regras

- `rental_id` explícitos de 100 001 a 1 100 000; no fim
  `setval('rental_rental_id_seq', max(rental_id))` (a sequência fica em 1 100 000).
- `inventory_id`, `customer_id` e `staff_id` escolhidos ao acaso entre os que existem.
  As FKs são recriadas no fim com `ADD CONSTRAINT ... FOREIGN KEY`, que verifica todas as linhas.
- `rental_date` entre 2022-01-01 e 2026-07-31: cada linha tem um segundo diferente
  (`random.sample`) mais meio segundo. Assim nunca há duas linhas iguais em
  `(rental_date, inventory_id, customer_id)`, nem com os alugueres que o Pagila já tem
  (o índice único também é recriado no fim e dava erro se houvesse repetidos).
- `return_date`: 2% `NULL`, o resto entre 1 e 240 horas depois de `rental_date`.
- semente fixa: `random.Random(42)`.
- rapidez: `COPY` para uma tabela temporária e depois um só `INSERT ... SELECT` para `rental`,
  sem FKs nem índices secundários (recriados no fim). Tudo numa transação.
- idempotente: se já há 1 000 000 linhas entre 100 001 e 1 100 000, não faz nada.

(O enunciado manda instalar `faker`. Não foi preciso: o `random` com semente fixa chega para estes
dados e é muito mais rápido; o Faker gera nomes e textos, que esta tabela não tem.)

## Tempos

```
ch04_a: 1,000,000 alugueres inseridos em 14.2 s     (real 0m14.604s)
ch04_b: 1,000,000 alugueres inseridos em 15.0 s     (real 0m15.422s)
```

Os dois abaixo dos 30 s.

## Checksums

```
== ch04_a
  rows   |             checksum
---------+----------------------------------
 1000000 | f4e3c725f5fa0446607eadd4435d0e2a

== ch04_b
  rows   |             checksum
---------+----------------------------------
 1000000 | f4e3c725f5fa0446607eadd4435d0e2a
```

Iguais: as duas bases têm exatamente as mesmas linhas novas.

Verificação das regras em `ch04_a`:

```
 nulls | bad |           min            |           max
-------+-----+--------------------------+--------------------------
 19990 |   0 | 2022-01-01 00:03:23.5+00 | 2026-07-30 23:59:47.5+00

 last_value
------------
    1100000
```

(`bad` = linhas com `return_date <= rental_date`.)

## Idempotência

Antes da 2.ª execução em `ch04_a`: `1000000 | f4e3c725f5fa0446607eadd4435d0e2a`.

```
ch04_a: as 1,000,000 linhas já existem, nada a fazer
  rows   |             checksum
---------+----------------------------------
 1000000 | f4e3c725f5fa0446607eadd4435d0e2a
```

A contagem e o checksum não mudaram.
