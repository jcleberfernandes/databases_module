# Exercício 14 — Pipelines de agregação e backup do MongoDB

Ficheiros: `pipelines.js` (as 4 pipelines), `backup_mongo.sh`, `restore_mongo.sh`.

## Como correr (na raiz do repositório)

```bash
# mongosh no contentor, base pagila_docs (usa o utilizador e a password do próprio contentor)
m() { docker compose exec -T mongo sh -c 'mongosh -u "$MONGO_INITDB_ROOT_USERNAME" -p "$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase admin --quiet pagila_docs --eval "$1"' -- "$1"; }
# films e rentals de uma cópia nova do Pagila (load.py do exercício 13)
./scripts/create-db.sh ex13 --pagila --reset
m 'db.films.drop(); db.customers.drop(); db.rentals.drop()'
(cd exercises/13-mongo/exercise && uv run python load.py)

m "$(cat exercises/14-pipelines/exercise/pipelines.js)"
bash exercises/14-pipelines/exercise/backup_mongo.sh
bash exercises/14-pipelines/exercise/restore_mongo.sh
```

## 1. Receita por categoria por mês em 2025 — 192 documentos

`$match` 2025 → `$unwind: "$categories"` → `$group` por categoria e `$dateTrunc` do mês com `$sum: "$amount"` → `$project` → `$sort`.

```js
{ revenue: Decimal128('333.87'), category: 'Action', month: '2025-01' }
{ revenue: Decimal128('342.98'), category: 'Action', month: '2025-02' }
{ revenue: Decimal128('385.83'), category: 'Action', month: '2025-03' }
```

**Porque dá 333.87 e não 314.94 (questão 2 do exercício 05).** São as mesmas tabelas,
mas o mês é escolhido por uma data diferente:

- aqui o mês é o da **`rental_date`** — o `amount` de cada aluguer é a soma dos pagamentos
  desse aluguer, e fica no mês em que o filme foi alugado;
- no exercício 05 a receita é por **`payment_date`** — o mês em que o pagamento foi feito.

Um aluguer feito no fim de janeiro e pago em fevereiro conta em janeiro aqui e em fevereiro no
exercício 05 (e vice-versa com dezembro). Confirmei no PostgreSQL:

```
        k         |  sum
------------------+--------
 por payment_date | 314.94
 por rental_date  | 333.87
```

## 2. Ator com mais filmes em cada categoria (com empates) — 16 documentos, 30 atores

`$unwind` de `categories` e de `actors` → `$group` por (categoria, ator) → `$group` por
categoria com `$max` e `$push` → `$filter` só os que têm o máximo (assim os empates ficam todos).

```js
{ category: 'Action',    films: 10, actors: [ { actor_id: 65, name: 'ANGELA HUDSON' }, { actor_id: 181, name: 'MATTHEW CARREY' } ] }
{ category: 'Animation', films: 10, actors: [ { actor_id: 13, name: 'UMA WOOD' }, { actor_id: 150, name: 'JAYNE NOLTE' } ] }
{ category: 'Children',  films: 9,  actors: [ { actor_id: 105, name: 'SIDNEY CROWE' }, { actor_id: 133, name: 'RICHARD PENN' },
                                              { actor_id: 139, name: 'EWAN GOODING' } ] }
total de atores: 30
```

## 3. Distribuição das durações (`$bucket`) — 5 documentos

```js
{ _id: 0,   films: 96 }
{ _id: 60,  films: 224 }
{ _id: 90,  films: 214 }
{ _id: 120, films: 216 }
{ _id: 150, films: 250 }
```

## 4. `$facet` — 1 documento

```js
{
  totals:    [ { films: 1000, avg_rental_rate: Decimal128('2.98') } ],
  by_rating: [ { films: 178, rating: 'G' }, { films: 210, rating: 'NC-17' }, { films: 194, rating: 'PG' },
               { films: 223, rating: 'PG-13' }, { films: 195, rating: 'R' } ],
  longest:   [ { title: 'CHICAGO NORTH', length: 185 }, { title: 'CONTROL ANTHEM', length: 185 },
               { title: 'DARN FORRESTER', length: 185 }, { title: 'GANGS PRIDE', length: 185 },
               { title: 'HOME PITY', length: 185 } ]
}
```

(Os documentos estão compactados aqui; o `mongosh` mostra um campo por linha.)

## 5. Backup e restore

`backup_mongo.sh` corre `mongodump --db pagila_docs --archive --gzip` no contentor e grava em
`backups/mongo_pagila_docs_<data>.archive.gz`. `restore_mongo.sh` pega no arquivo mais recente,
corre `mongorestore --archive --gzip --drop --nsFrom 'pagila_docs.*' --nsTo 'pagila_docs_restored.*'`
e compara as contagens. As credenciais são as do próprio contentor (não estão nos scripts).

```
backup: backups/mongo_pagila_docs_2026-11-04_205732.archive.gz (5.6M)
restaurar: backups/mongo_pagila_docs_2026-11-04_205732.archive.gz -> pagila_docs_restored
coleção           pagila_docs     restored
customers                 999          999 OK
films                    1000         1000 OK
rental_buckets           1605         1605 OK
rental_history            997          997 OK
rentals                 51805        51805 OK
todas as coleções têm o mesmo nº de documentos
```

(`rental_buckets` e `rental_history` são do challenge 13; o backup leva a base inteira.)
