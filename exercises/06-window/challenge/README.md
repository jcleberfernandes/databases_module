# Challenge 06 — Gaps and islands

Ficheiro: `gaps_islands.sql`.

```bash
docker compose exec -T postgres psql -U postgres -d ex06 -v ON_ERROR_STOP=1 < exercises/06-window/challenge/gaps_islands.sql
```

Ideia:

1. `months`: uma linha por cliente e mês em que alugou.
2. `numbered`: mês em número (`ano*12 + mês`) menos `row_number()`. Meses
   seguidos dão sempre o mesmo valor (a "ilha"); um mês em falta muda o valor.
3. `islands`: agrupa por ilha → início, fim e nº de meses.
4. `best`: `row_number()` para ficar só com a maior ilha de cada cliente.

Resultado (10 clientes com a maior sequência):

```
 customer_id | first_name | last_name | months | start_month | end_month
-------------+------------+-----------+--------+-------------+------------
          70 | CHRISTINA  | RAMIREZ   |     19 | 2023-06-01  | 2024-12-01
         547 | KURT       | EMMONS    |     18 | 2022-05-01  | 2023-10-01
         567 | ALFREDO    | MCADAMS   |     18 | 2022-06-01  | 2023-11-01
          33 | ANNA       | HILL      |     17 | 2023-07-01  | 2024-11-01
         158 | VERONICA   | STONE     |     17 | 2022-11-01  | 2024-03-01
         299 | JAMES      | GANNON    |     17 | 2022-05-01  | 2023-09-01
         443 | FRANCISCO  | SKIDMORE  |     17 | 2023-07-01  | 2024-11-01
         533 | JESSIE     | MILAM     |     17 | 2023-04-01  | 2024-08-01
         740 | SOFIA      | MUELLER   |     17 | 2024-07-01  | 2025-11-01
         556 | ARMANDO    | GRUBER    |     16 | 2023-09-01  | 2024-12-01
(10 rows)
```
