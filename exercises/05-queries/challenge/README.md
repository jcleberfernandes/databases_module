# Challenge 05 — Graus de separação entre atores

Ficheiro: `degrees.sql` (`WITH RECURSIVE`).

```bash
docker compose exec -T postgres psql -U postgres -d ex05 < exercises/05-queries/challenge/degrees.sql
```

- `costar`: pares de atores que entraram no mesmo filme (distância 1).
- `walk`: começa no ator 1 e, a cada passo, vai para os colegas de filme.
- **Termina** porque `distance < 3` impede um 4.º passo.
- **Não revisita** porque cada caminho guarda `visited` (array) e
  `c.b <> ALL (w.visited)` impede voltar a um ator que já está no caminho.
- No fim, `min(distance)` dá a distância mais curta para cada ator.

Resultado para o ator 1 (PENELOPE GUINESS), 199 linhas, ~1,5 s:

```
 actor_id | first_name  |  last_name   | shortest_distance
----------+-------------+--------------+-------------------
        4 | JENNIFER    | DAVIS        |                 1
        6 | BETTE       | NICHOLSON    |                 1
        7 | GRACE       | MOSTEL       |                 1
...
      200 | THORA       | TEMPLE       |                 2
(199 rows)
```

Resumo: 79 atores a distância 1 e 120 a distância 2. Todos os outros
199 atores estão a 2 graus ou menos, por isso não aparece nenhum a distância 3.
