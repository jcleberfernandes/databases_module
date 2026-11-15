# Exercício 05 — Joins, agregação, subqueries e CTEs

Ficheiro: `queries.sql` (as 10 queries, cada uma com o número e a pergunta num comentário). Sem window functions.

```bash
./scripts/create-db.sh ex05 --pagila --reset
docker compose exec -T postgres psql -U postgres -d ex05 -v ON_ERROR_STOP=1 < exercises/05-queries/exercise/queries.sql
```

| # | Linhas | Esperado | Valor conferido |
|---|---|---|---|
| 1 | 16 | 16 | Drama 152, Music 152 |
| 2 | 192 | 192 | Action 2025-01 = 314.94 |
| 3 | 42 | 42 | |
| 4 | 908 | 908 | |
| 5 | 143 | 143 | |
| 6 | 7 | 7 | Mexico 430 clientes |
| 7 | 449 | 449 | |
| 8 | 14 | 14 | |
| 9 | 49 | 49 | |
| 10 | 16 | 16 | Sci-Fi 5.30 |

Todas batem com o esperado. Notas:
- **3** usa `NOT EXISTS` sobre `inventory JOIN rental`: um filme sem cópias também não tem alugueres, por isso entra.
- **6** soma os pagamentos por cliente **antes** do join com os países, para não contar o mesmo cliente várias vezes.
- **7** usa `coalesce(..., 0)` para os clientes sem pagamentos contarem como 0 na média.
- **8** usa uma subquery correlacionada (`length = (SELECT max(length) ... WHERE rating = f.rating)`), que mantém os empates.

## Contagem e as 5 primeiras linhas de cada resultado

### 1. Filmes por categoria, incluindo categorias sem filmes — esperado 16 linhas, Drama e Music com 152

```
  category   | films 
-------------+-------
 Drama       |   152
 Music       |   152
 Travel      |   151
 Children    |   150
 Foreign     |   150
...
(16 rows)
```

### 2. Receita por categoria por mês em 2025 (payment_date) — esperado 192 linhas, Action jan/2025 = 314.94

```
  category   |   month    | revenue 
-------------+------------+---------
 Action      | 2025-01-01 |  314.94
 Action      | 2025-02-01 |  317.99
 Action      | 2025-03-01 |  370.90
 Action      | 2025-04-01 |  379.83
 Action      | 2025-05-01 |  384.76
...
(192 rows)
```

### 3. Filmes nunca alugados, incluindo sem cópias — esperado 42

```
 film_id |         title          
---------+------------------------
      14 | ALICE FANTASIA
      33 | APOLLO TEEN
      36 | ARGONAUTS TOWN
      38 | ARK RIDGEMONT
      41 | ARSENIC INDEPENDENCE
...
(42 rows)
```

### 4. Clientes que alugaram filmes das 5 classificações — esperado 908

```
 customer_id | first_name  |  last_name   
-------------+-------------+--------------
           1 | MARY        | SMITH
           2 | PATRICIA    | JOHNSON
           3 | LINDA       | WILLIAMS
           4 | BARBARA     | JONES
           5 | ELIZABETH   | BROWN
...
(908 rows)
```

### 5. Pares de atores com mais de 3 filmes juntos (self join) — esperado 143

```
 actor_1 |       name_1        | actor_2 |       name_2       | films 
---------+---------------------+---------+--------------------+-------
      27 | JULIA MCQUEEN       |      60 | HENRY BERRY        |     7
      15 | CUBA OLIVIER        |     198 | MARY KEITEL        |     6
      21 | KIRSTEN PALTROW     |     108 | WARREN NOLTE       |     6
      37 | VAL BOLGER          |     188 | ROCK DUKAKIS       |     6
      83 | BEN WILLIS          |     161 | HARVEY HOPE        |     6
...
(143 rows)
```

### 6. Países com mais de 20 clientes — esperado 7 linhas, a 1.ª Mexico com 430

```
      country       | customers | total_paid 
--------------------+-----------+------------
 Mexico             |       430 |   35650.03
 India              |        60 |   14182.51
 China              |        53 |   12389.30
 United States      |        36 |    8618.76
 Japan              |        31 |    7287.91
...
(7 rows)
```

### 7. Clientes que pagaram mais do que a média do seu país — esperado 449

```
 customer_id | first_name  |  last_name   |                country                |  paid  | country_avg 
-------------+-------------+--------------+---------------------------------------+--------+-------------
         176 | JUNE        | CARROLL      | Algeria                               | 280.26 |      253.64
         528 | CLAUDE      | HERZOG       | Angola                                | 256.30 |      226.82
         359 | WILLIE      | MARKHAM      | Argentina                             | 293.17 |      241.67
          89 | JULIA       | FLORES       | Argentina                             | 284.22 |      241.67
         560 | JORDAN      | ARCHULETA    | Argentina                             | 273.27 |      241.67
...
(449 rows)
```

### 8. Filmes mais longos de cada classificação, com empates — esperado 14

```
 rating | film_id |       title        | length 
--------+---------+--------------------+--------
 G      |     182 | CONTROL ANTHEM     |    185
 G      |     212 | DARN FORRESTER     |    185
 G      |     609 | MUSCLE BRIGHT      |    185
 PG     |     991 | WORST BANGER       |    185
 PG-13  |     141 | CHICAGO NORTH      |    185
...
(14 rows)
```

### 9. Clientes sem alugueres a partir de 2026-04-01 — esperado 49

```
 customer_id | first_name |  last_name  
-------------+------------+-------------
           9 | MARGARET   | MOORE
          13 | KAREN      | JACKSON
          21 | MICHELLE   | CLARK
          46 | CATHERINE  | CAMPBELL
          52 | JULIE      | SANCHEZ
...
(49 rows)
```

### 10. Média de dias fora por categoria — esperado 16 linhas, a 1.ª Sci-Fi com 5.30

```
  category   | avg_days_out 
-------------+--------------
 Sci-Fi      |         5.30
 Music       |         5.27
 Sports      |         5.26
 Drama       |         5.18
 Children    |         5.17
...
(16 rows)
```

