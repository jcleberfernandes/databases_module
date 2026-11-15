# Challenge 13 — Padrão bucket

Ficheiros:
- `buckets.py` — `add_rental()`, carga de `rental_buckets`, criação de `rental_history` e a comparação do cliente 380.
- `pyproject.toml` (reutiliza o `config.py` do exercício).

```bash
# precisa da coleção rentals do exercício (uv run python load.py em ../exercise)
cd exercises/13-mongo/challenge && uv run python buckets.py
```

## 1. Desenho de `rental_buckets`

```js
{
  _id: ObjectId("..."),
  customer_id: 380,
  seq: 1,          // 0, 1, 2, ... por cliente
  count: 47,       // nº de alugueres no bucket (no máximo 50)
  rentals: [ { rental_id, film_id, title, rental_date, return_date, amount }, ... ]
}
```

Índice único `{customer_id: 1, seq: 1}`: serve para ler os buckets de um cliente por ordem
e impede dois buckets com o mesmo `seq`.

## 2. `add_rental` com um só `updateOne`

```python
buckets.update_one(
    {"customer_id": customer_id, "count": {"$lt": 50}},          # só um bucket com espaço
    {"$push": {"rentals": rental}, "$inc": {"count": 1},
     "$setOnInsert": {"seq": next_seq}},                           # só se abrir um bucket novo
    upsert=True,
)
```

**Porque é seguro com duas chamadas ao mesmo tempo para o mesmo cliente:**

- Cada `updateOne` é atómico num documento: o `$push` e o `$inc` acontecem juntos, e o
  filtro `count < 50` é verificado no momento da escrita. Se duas chamadas encontram o
  bucket com 49, a primeira deixa-o com 50; a segunda, ao escrever, já não cumpre o filtro e
  o MongoDB volta a avaliá-lo — não há bucket com espaço, por isso faz upsert de um novo.
  Um bucket nunca passa de 50.
- O risco que sobra é **duas chamadas abrirem um bucket novo ao mesmo tempo** (as duas não
  encontram bucket com espaço e as duas fazem upsert). Sem mais nada, ficavam dois buckets
  meio vazios com o mesmo `seq`. O **índice único `{customer_id, seq}`** impede isso: a
  segunda inserção dá `DuplicateKeyError`, e `add_rental` repete — desta vez o filtro
  encontra o bucket que a outra acabou de abrir.

## 3. Carga

```
rental_buckets: 51805 alugueres em 1605 buckets (83.1 s)
rental_history: 997 documentos
maior bucket: 50 alugueres (máximo 50)
cliente 380: {'count': 50, 'seq': 0}
cliente 380: {'count': 47, 'seq': 1}
```

(83 s porque são 51 805 `updateOne` um a um, de propósito, por ordem de `rental_date`.)

## 4. `rental_history`

Um `aggregate` com `$sort` por `rental_date`, `$group` por cliente com `$push` de todos os
alugueres, e `$out: "rental_history"`. 997 documentos (dois clientes não têm alugueres).

## 5. Cliente 380 (97 alugueres)

```
rental_buckets seq=0 count=50 tamanho=6494 bytes
rental_buckets seq=1 count=47 tamanho=6136 bytes
rental_history count=97 tamanho=12533 bytes
rental_buckets: 20 alugueres, o mais recente 86888 | 0.632 ms por leitura (média de 1000)
rental_history: 20 alugueres, o mais recente 86888 | 0.491 ms por leitura (média de 1000)
```

O tamanho é `len(bson.encode(doc))`, o mesmo valor que `Object.bsonsize()` no mongosh.
Os 20 mais recentes: em `rental_buckets` lê-se só o último bucket com `$slice: -20`
(e o anterior só se o último tiver menos de 20); em `rental_history`, o documento do cliente com `$slice: -20`.

**Resultado:** com 97 alugueres os tempos são praticamente iguais (~0,5 ms; o history até é um
pouco mais rápido porque não precisa de ordenar por `seq`). O documento do history já tem o dobro
do tamanho de um bucket, mas 12 KB ainda é pequeno.

## Quando compensa o padrão bucket

Quando o histórico **cresce sem limite**. Com um documento por cliente:
- o documento cresce sempre e pode chegar ao limite de 16 MB;
- cada `$push` reescreve um documento cada vez maior, e cada leitura do cliente traz (ou
  tem de percorrer) o histórico todo;
- documentos muito diferentes em tamanho gastam mais memória na cache.

Com buckets, cada documento tem no máximo 50 entradas: tamanho limitado, escritas sempre
baratas (só o último bucket muda), e ler "os mais recentes" é ler 1 documento pequeno. Para
históricos pequenos como o do Pagila (máx. 97) não há ganho visível; o ganho aparece com
milhares de entradas por cliente (sensores, logs, mensagens de um chat).
