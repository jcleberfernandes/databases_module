# Exercício 13 — Pagila em documentos MongoDB

Ficheiros:
- `load.py` — lê o Pagila e escreve `films`, `customers` e `rentals` em `pagila_docs`.
- `operations.js` — as 8 operações.
- `validation.js` — validador `$jsonSchema` em `films` e os dois inserts inválidos.
- `index.js` — `explain` antes e depois do índice em `actors.actor_id`.
- `config.py`, `pyproject.toml`, `.env.example` — `DATABASE_URL` e `MONGO_URL` (sem `.env`, usa as passwords do `.env` da raiz).

## Como correr (na raiz do repositório)

```bash
# mongosh no contentor, base pagila_docs (usa o utilizador e a password do próprio contentor)
m() { docker compose exec -T mongo sh -c 'mongosh -u "$MONGO_INITDB_ROOT_USERNAME" -p "$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase admin --quiet pagila_docs --eval "$1"' -- "$1"; }
./scripts/create-db.sh ex13 --pagila --reset
m 'db.films.drop(); db.customers.drop(); db.rentals.drop()'     # começar com as coleções vazias
(cd exercises/13-mongo/exercise && uv run python load.py)
m "$(cat exercises/13-mongo/exercise/operations.js)"
m "$(cat exercises/13-mongo/exercise/validation.js)"
(cd exercises/13-mongo/exercise && uv run python load.py)            # continua a funcionar com o validador
m "$(cat exercises/13-mongo/exercise/index.js)"
```

## 1. `load.py`

```
films        1000 documentos  (novos=1000, alterados=0) em 0.1 s
customers     999 documentos  (novos=999, alterados=0) em 0.1 s
rentals     51805 documentos  (novos=51805, alterados=0) em 2.3 s
```

Segunda execução — os mesmos documentos, nada muda:

```
films        1000 documentos  (novos=0, alterados=0) em 0.1 s
customers     999 documentos  (novos=0, alterados=0) em 0.1 s
rentals     51805 documentos  (novos=0, alterados=0) em 1.6 s
```

O `_id` de cada documento é o id do Pagila e cada documento é escrito com
`ReplaceOne(..., upsert=True)` (num `bulk_write`). Dinheiro em `Decimal128`, datas como datas BSON.

Os documentos de exemplo ficam iguais aos do enunciado (`film 1`, `customer 1`, `rental 87420`), por exemplo:

```js
{ _id: 87420, customer_id: 1, film_id: 307, title: 'FELLOWSHIP AUTUMN',
  categories: [ 'Children', 'Family', 'Sci-Fi' ], store_id: 1,
  rental_date: ISODate('2026-07-23T01:38:34.193Z'), return_date: null, amount: Decimal128('0') }
```

### Porquê esta forma

- **Atores e categorias embutidos em `films`.** São poucos por filme (média ~5 atores, 1–3
  categorias), não crescem com o tempo e quase sempre se leem juntos com o filme. Embutir
  dá o filme completo numa só leitura, sem joins. O nome do ator repete-se em vários filmes,
  mas muda muito raramente.
- **Só 10 alugueres em `customers`.** O histórico de um cliente cresce sem limite; se estivesse
  todo no documento, este ficava cada vez maior (o limite é 16 MB) e cada leitura do cliente
  trazia tudo. Os 10 mais recentes chegam para a página do cliente ("o que alugou ultimamente")
  e mantêm o documento pequeno e com tamanho fixo.
- **Histórico completo em `rentals`.** Um documento por aluguer é o sítio certo para dados que
  crescem sempre e que se consultam de muitas formas (por cliente, por filme, por data, por
  categoria). Com índices, `rentals` responde a essas perguntas; os relatórios do exercício 14
  usam esta coleção.

## 2. `operations.js`

| # | Operação | Resultado |
|---|---|---|
| 1 | `countDocuments({rating: "PG-13", length: {$gt: 120}})` | **118** |
| 2 | `countDocuments({"actors.actor_id": 1})` | **19** |
| 3 | `countDocuments({categories: "Horror", rental_rate: NumberDecimal("0.99")})` | **43** |
| 4 | `countDocuments({recent_rentals: {$elemMatch: {return_date: null}}})` | **56** |
| 5 | projeção `first_name`, `last_name`, `recent_rentals.title` do cliente 1 | 1 documento, 10 títulos |
| 6 | `updateMany` NC-17 < 60 min, `$inc: {rental_rate: NumberDecimal("0.50")}` | **modifiedCount: 21** |
| 7 | `$push` com `$each`, `$position: 0`, `$slice: 10` no cliente 1 | 10 itens, o 1.º é o novo |
| 8 | `updateOne({_id: 1001}, {$setOnInsert: {title: "TEST FILM"}}, {upsert: true})` × 2 | 1.ª: upsert 1; 2.ª: matched 1, modified 0 |

Saída:

```
1. PG-13 com mais de 120 minutos
118
2. filmes do ator 1
19
3. Horror com rental_rate 0.99
43
4. clientes com um aluguer por devolver em recent_rentals ($elemMatch)
56
5. cliente 1: nome e títulos de recent_rentals (projeção)
{
  first_name: 'MARY',
  last_name: 'SMITH',
  recent_rentals: [
    { title: 'FELLOWSHIP AUTUMN' },   { title: 'FUGITIVE MAGUIRE' },
    { title: 'CHASING FIGHT' },       { title: 'GLEAMING JAWBREAKER' },
    { title: 'SECRET GROUNDHOG' },    { title: 'MULAN MOON' },
    { title: 'BRAVEHEART HUMAN' },    { title: 'SPLENDOR PATTON' },
    { title: 'DRACULA CRYSTAL' },     { title: 'SHAKESPEARE SADDLE' }
  ]
}
6. +0.50 no rental_rate dos NC-17 com menos de 60 minutos
{ acknowledged: true, insertedId: null, matchedCount: 21, modifiedCount: 21, upsertedCount: 0 }
7. novo aluguer à frente de recent_rentals do cliente 1, ficando só 10
{ acknowledged: true, insertedId: null, matchedCount: 1, modifiedCount: 1, upsertedCount: 0 }
recent_rentals: 10 | primeiro: 999999 ACADEMY DINOSAUR
8. upsert com $setOnInsert, 2 vezes
execução 1: matched=0 modified=0 upserted=1
execução 2: matched=1 modified=0 upserted=0
```

(O output da 5 está em 2 colunas aqui para ficar curto; o `mongosh` mostra um título por linha.)

## 3. Validação

`validationLevel: "strict"`, `validationAction: "error"`, com as regras do enunciado
(`title` string, `rating` enum, `length` int 1–999, `rental_rate` decimal, `categories`
array de strings, `actors` array de `{actor_id: int, name: string}`). Só `title` é
obrigatório, para o `TEST FILM` da operação 8 continuar válido.

```
validador aplicado a films
rating: "XXX": REJEITADO -> "Document failed validation" (code 121) | campo "rating": [{"operatorName":"enum","specifiedAs":{"enum":["G","PG","PG-13","R","NC-17"]},"reason":"value was not found in enum","consideredValue":"XXX"}]
length: "long": REJEITADO -> "Document failed validation" (code 121) | campo "length": [{"operatorName":"bsonType","specifiedAs":{"bsonType":"int"},"reason":"type did not match","consideredValue":"long","consideredType":"string"}]
```

`load.py` com o validador ativo (repõe também o que as operações 6 e 7 mudaram):

```
films        1000 documentos  (novos=0, alterados=21) em 0.0 s
customers     999 documentos  (novos=0, alterados=1) em 0.0 s
rentals     51805 documentos  (novos=0, alterados=0) em 1.5 s
```


## 4. Índice em `actors.actor_id`

```
ANTES : stage=COLLSCAN totalDocsExamined=1001 totalKeysExamined=0 nReturned=19 ms=81
DEPOIS: stage=FETCH <- IXSCAN totalDocsExamined=19 totalKeysExamined=19 nReturned=19 ms=1
```

Sem índice o MongoDB lê os 1001 documentos (1000 filmes + o `TEST FILM`) para devolver 19.
Com o índice multikey em `actors.actor_id` vai direto às 19 entradas do ator 1 e só lê esses 19 documentos.
