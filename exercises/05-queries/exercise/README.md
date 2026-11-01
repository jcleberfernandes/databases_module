# Exercício 05 — Joins, agregação, subqueries e CTEs

Ficheiro: `queries.sql` (10 perguntas de negócio).

```bash
./scripts/create-db.sh ex05 --pagila
docker compose exec -T postgres psql -U postgres -d ex05 -v ON_ERROR_STOP=1 < exercises/05-queries/exercise/queries.sql
```

| # | Pergunta | Técnica | Linhas |
|---|---|---|---|
| 1 | Receita por categoria por mês (primeiras 20) | joins + GROUP BY | 20 |
| 2 | Top 5 clientes por loja | CTE + row_number | 10 (só 2 lojas têm clientes) |
| 3 | Filmes nunca alugados | NOT EXISTS | 42 |
| 4 | Pares de atores com mais de 3 filmes juntos | self join + HAVING | 143 |
| 5 | Clientes que gastam mais do que a média da cidade | 2 CTEs | 182 |
| 6 | Filmes por categoria | GROUP BY | 16 |
| 7 | 10 filmes mais alugados | joins + LIMIT | 10 |
| 8 | Clientes com mais alugueres por devolver | WHERE IS NULL | 10 |
| 9 | Atores que nunca fizeram Horror | NOT IN (subquery) | 4 |
| 10 | Receita por país (top 10) | 5 joins | 10 |
