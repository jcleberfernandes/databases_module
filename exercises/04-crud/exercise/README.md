# Exercício 04 — CRUD

Ficheiro: `queries.sql` (12 operações em Pagila, com o resultado esperado em comentário).

```bash
./scripts/create-db.sh ex04 --pagila
docker compose exec -T postgres psql -U postgres -d ex04 -v ON_ERROR_STOP=1 < exercises/04-crud/exercise/queries.sql
```

| # | Operação | Esperado |
|---|---|---|
| 1 | Filmes PG-13 com mais de 120 min, por título | 118 linhas |
| 2 | Clientes sem alugueres no último ano | 2 linhas |
| 3 | Filmes por classificação | 5 linhas |
| 4 | 10 filmes mais longos | 10 linhas (185 min) |
| 5 | INSERT de ator com RETURNING | actor_id 201 |
| 6 | UPDATE do preço da categoria Horror com RETURNING | 142 linhas |
| 7 | Upsert de ator (2 vezes) | 1 linha cada vez |
| 8 | Upsert de contador de visualizações | views = 2 |
| 9 | INSERT de 3 pagamentos de teste | 3 linhas |
| 10 | DELETE dos pagamentos de teste, com SELECT antes | 3 e DELETE 3 |
| 11 | Clientes inativos | 44 linhas |
| 12 | Atores com apelido começado por S | 9 linhas |
