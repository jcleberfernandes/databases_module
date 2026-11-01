# Challenge 03 — DOMAIN isbn13

Ficheiro: `isbn.sql` (cria a função `is_valid_isbn13`, o domínio `isbn13` e usa-o em `book.isbn`).

```bash
docker compose exec -T postgres psql -U postgres -d ex03 < exercises/03-ddl/challenge/isbn.sql
```

Resultado:

```
INSERT 0 1
       isbn        |    title
-------------------+-------------
 978-0-306-40615-7 | ISBN válido
(1 row)

ERROR:  value for domain isbn13 violates check constraint "isbn13_check"
```

## Porquê `IMMUTABLE`?

A função só depende do valor de entrada (não lê tabelas nem a hora atual),
logo o resultado para o mesmo ISBN é sempre o mesmo. Marcar como `IMMUTABLE`
diz isso ao PostgreSQL: pode usá-la em `CHECK`, em domínios e em índices,
e o planner pode calcular o resultado uma só vez. Se a função mudasse de
resultado com o tempo, linhas antigas que já passaram no `CHECK` podiam ficar
inválidas sem ninguém saber.
