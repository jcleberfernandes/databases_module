# Challenge 06 — Gaps and islands

Ficheiro: `islands.sql`.

```bash
./scripts/create-db.sh ch06 --pagila --reset
docker compose exec -T postgres psql -U postgres -d ch06 < exercises/06-window/challenge/islands.sql
```

## Resultado (os 10 clientes com a ilha mais longa)

```
 customer_id | first_month | last_month | months 
-------------+-------------+------------+--------
          70 | 2023-06     | 2024-12    |     19
         547 | 2022-05     | 2023-10    |     18
         567 | 2022-06     | 2023-11    |     18
          33 | 2023-07     | 2024-11    |     17
         158 | 2022-11     | 2024-03    |     17
         299 | 2022-05     | 2023-09    |     17
         443 | 2023-07     | 2024-11    |     17
         533 | 2023-04     | 2024-08    |     17
         740 | 2024-07     | 2025-11    |     17
         556 | 2023-09     | 2024-12    |     16
(10 rows)

```

A 1.ª linha é o cliente 70 com 19 meses (2023-06 a 2024-12) e a 10.ª o cliente 556 com 16 meses.

## A técnica para agrupar meses seguidos

1. `months`: uma linha por cliente e por mês em que alugou (`DISTINCT` sobre `date_trunc('month', rental_date)`).
2. `numbered`: para cada linha, o **nº do mês** (`ano * 12 + mês`) menos o **`row_number()`**
   dos meses desse cliente por ordem. Em meses seguidos os dois sobem 1 de cada vez, por isso a
   diferença fica igual: é o identificador da ilha. Quando falta um mês, o nº do mês salta 2 e o
   `row_number` só 1, e a diferença muda — começa outra ilha.

   | mês | nº do mês | row_number | diferença |
   |---|---|---|---|
   | 2023-06 | 24282 | 1 | 24281 |
   | 2023-07 | 24283 | 2 | 24281 |
   | 2023-09 | 24285 | 3 | **24282** ← falta agosto: ilha nova |

   (Março e abril de 2022 não têm alugueres nenhuns: as ilhas partem-se sempre aí.)
3. `islands`: `GROUP BY` cliente e diferença → `min(month)`, `max(month)` e `count(*)` de cada ilha.
4. `longest`: `row_number() OVER (PARTITION BY customer_id ORDER BY months DESC, first_month)` e
   fica a posição 1 — a ilha mais longa e, em empate, a mais antiga.
5. Os 10 primeiros por `months DESC, customer_id`.

Só window functions (`row_number`), `DISTINCT` e `GROUP BY`: sem código procedimental nem CTE recursiva.
