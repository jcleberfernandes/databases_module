# Exercício 04 — CRUD, upsert e transações

Ficheiro: `queries.sql` (as 12 operações, numeradas `-- 1.` a `-- 12.`).

```bash
./scripts/create-db.sh ex04 --pagila --reset
docker compose exec -T postgres psql -U postgres -d ex04 -v ON_ERROR_STOP=1 < exercises/04-crud/exercise/queries.sql
```

Corre do princípio ao fim sem erros numa cópia nova. Os resultados batem todos com os esperados:

| # | Operação | Resultado | Esperado |
|---|---|---|---|
| 1 | PG-13 com mais de 120 min, por título | 118 linhas, `APOLLO TEEN` … `WRONG BEHAVIOR` | 118, `APOLLO TEEN` … `WRONG BEHAVIOR` |
| 2 | apelido com `son` (`ILIKE`) | 9 linhas | 9 |
| 3 | alugueres não devolvidos | 241 linhas | 241 |
| 4 | `DISTINCT rental_duration` | 5 linhas, 3 … 7 | 5, 3 … 7 |
| 5 | 3.ª página por título (`LIMIT 10 OFFSET 20`) | `AMERICAN CIRCUS` … `ANYTHING SAVANNAH` | idem |
| 6 | janeiro de 2026 | 746 (`BETWEEN`) e 781 (`>= … <`) | 746 e 781 |
| 7 | `INSERT` ADA LOVELACE `RETURNING` | actor_id 201 | 201 |
| 8 | NC-17 < 60 min +0.50, em transação | `count` 21 e `UPDATE 21` | 21 |
| 9 | upsert de prémios, 2 vezes | awards 1, depois 2 | 2 |
| 10 | `ON CONFLICT DO NOTHING`, 2 vezes | `INSERT 0 1`, depois `INSERT 0 0` | 1 e 0 |
| 11 | 3 pagamentos de teste `RETURNING` | 3 linhas | 3 |
| 12 | `SELECT count(*)` e `DELETE … RETURNING`, em transação | 3 e `DELETE 3` | 3 |

## Output de cada operação

**1.** 118 linhas

```
            title            | length
-----------------------------+--------
 APOLLO TEEN                 |    153
 ...
 WRONG BEHAVIOR              |    178
(118 rows)
```

**2.** 9 linhas

```
 actor_id | first_name | last_name
----------+------------+-----------
      154 | MERYL      | GIBSON
       65 | ANGELA     | HUDSON
      146 | ALBERT     | JOHANSSON
        8 | MATTHEW    | JOHANSSON
       64 | RAY        | JOHANSSON
       61 | CHRISTIAN  | NEESON
       62 | JAYNE      | NEESON
        6 | BETTE      | NICHOLSON
      168 | WILL       | WILSON
(9 rows)
```

**3.** 241 linhas

```
 rental_id |          rental_date          | customer_id
-----------+-------------------------------+-------------
     11496 | 2022-02-14 15:16:03+00        |         155
 ...
     87534 | 2026-07-27 04:40:26.294744+00 |         235
(241 rows)
```

**4.** 5 linhas

```
 rental_duration
-----------------
               3
               4
               5
               6
               7
(5 rows)
```

**5.** 10 linhas

```
 film_id |        title
---------+----------------------
      21 | AMERICAN CIRCUS
      22 | AMISTAD MIDSUMMER
      23 | ANACONDA CONFESSIONS
      24 | ANALYZE HOOSIERS
      25 | ANGELS LIFE
      26 | ANNIE IDENTITY
      27 | ANONYMOUS HUMAN
      28 | ANTHEM LUKE
      29 | ANTITRUST TOMATOES
      30 | ANYTHING SAVANNAH
(10 rows)
```

**6.**

```
 with_between
--------------
          746

 with_half_open_range
----------------------
                  781
```

Porque são diferentes: `rental_date` é um `timestamptz`, e `BETWEEN '2026-01-01' AND '2026-01-31'`
compara com `2026-01-31 00:00:00`. Tudo o que foi alugado no dia 31 depois da meia-noite fica de
fora (35 alugueres). A forma `>= '2026-01-01' AND < '2026-02-01'` apanha o mês inteiro, qualquer
que seja a hora: **é a correta**.

**7.**

```
 actor_id
----------
      201
(1 row)
INSERT 0 1
```

**8.**

```
BEGIN
 count
-------
    21
(1 row)

 film_id |        title        | rental_rate
---------+---------------------+-------------
       3 | ADAPTATION HOLES    |        3.49
 ...
    1000 | ZORRO ARK           |        5.49
(21 rows)
UPDATE 21
COMMIT
```

**9.**

```
CREATE TABLE
 actor_id | awards
----------+--------
        1 |      1
INSERT 0 1
 actor_id | awards
----------+--------
        1 |      2
INSERT 0 1
```

**10.**

```
INSERT 0 1
INSERT 0 0
```

**11.**

```
 payment_id
------------
     102095
     102096
     102097
(3 rows)
INSERT 0 3
```

**12.**

```
BEGIN
 count
-------
     3
(1 row)

 payment_id
------------
     102095
     102096
     102097
(3 rows)
DELETE 3
COMMIT
```
