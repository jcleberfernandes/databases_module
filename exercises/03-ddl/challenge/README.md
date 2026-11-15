# Challenge 03 — DOMAIN isbn13

Ficheiro: `isbn.sql` (a função, o domínio, a tabela `book` do enunciado e os 7 inserts de teste).

```bash
./scripts/create-db.sh ch03
docker compose exec -T postgres psql -U postgres -d ch03 < exercises/03-ddl/challenge/isbn.sql
```

A função `is_valid_isbn13(text)`:

1. formato: `^[0-9](-?[0-9])*$` — começa e acaba num dígito, e cada hífen tem um dígito antes e
   depois (por isso nunca no início, no fim, nem dois seguidos);
2. 13 dígitos sem os hífens;
3. dígito de controlo: os 12 primeiros × 1, 3, 1, 3, …, somados; o último tem de ser `(10 - soma % 10) % 10`.

## Output

```
DROP TABLE
DROP DOMAIN
DROP FUNCTION
CREATE FUNCTION
CREATE DOMAIN
CREATE TABLE
INSERT 0 1
INSERT 0 1
INSERT 0 1
ERROR:  value for domain isbn13 violates check constraint "isbn13_check"
ERROR:  value for domain isbn13 violates check constraint "isbn13_check"
ERROR:  value for domain isbn13 violates check constraint "isbn13_check"
ERROR:  value for domain isbn13 violates check constraint "isbn13_check"
 book_id |       isbn        |  title   
---------+-------------------+----------
       1 | 978-0-306-40615-7 | válido 1
       2 | 9781402894626     | válido 2
       3 | 978-3-16-148410-0 | válido 3
(3 rows)

```

| Valor | Resultado |
|---|---|
| `978-0-306-40615-7` | aceite |
| `9781402894626` | aceite |
| `978-3-16-148410-0` | aceite |
| `978-0-306-40615-8` | rejeitado: dígito de controlo errado |
| `978-0-306-4061` | rejeitado: curto demais |
| `-9780306406157` | rejeitado: hífen no início |
| `978--0306406157` | rejeitado: dois hífens seguidos |

## Porque a função tem de ser `IMMUTABLE`

O `CHECK` de um domínio é verificado em cada `INSERT` e `UPDATE`, mas depois **não volta a
ser verificado** para as linhas que já estão gravadas. Isso só é correto se a função der sempre o
mesmo resultado para o mesmo valor — senão uma linha aceite hoje podia ser inválida amanhã sem
ninguém saber. `IMMUTABLE` é a promessa ao PostgreSQL de que a função só depende dos argumentos
(não lê tabelas, nem a data, nem configurações). Com essa garantia, o PostgreSQL também a pode
usar em índices (ex: um índice de expressão) e calcular o resultado uma só vez para constantes.
Esta função cumpre: só usa o texto que recebe.
