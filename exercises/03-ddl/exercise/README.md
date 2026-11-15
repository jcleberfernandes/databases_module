# Exercício 03 — DDL: a biblioteca em PostgreSQL

Ficheiros: `schema.sql` (todas as tabelas do modelo do exercício 02, com dados de exemplo) e
`invalid.sql` (5 instruções que têm de falhar).

```bash
./scripts/create-db.sh ex03
docker compose exec -T postgres psql -U postgres -d ex03 -v ON_ERROR_STOP=1 < exercises/03-ddl/exercise/schema.sql
docker compose exec -T postgres psql -U postgres -d ex03 < exercises/03-ddl/exercise/invalid.sql
```

O que o `schema.sql` tem (pedido no enunciado):

- chaves substitutas com `GENERATED ALWAYS AS IDENTITY`, dinheiro em `numeric(8,2)`, datas em `date` / `timestamptz`;
- `CHECK`: `copy_condition_check`, `reservation_status_check`, `book_year_check`, `fine_amount_check`, `loan_returned_check`;
- `UNIQUE` composto: `book_author_book_id_author_order_key` em `(book_id, author_order)`;
- `ON DELETE RESTRICT` (ex: `book_publisher_id_fkey`) e `ON DELETE CASCADE` (ex: `book_author_book_id_fkey`), cada um justificado num comentário;
- `due_on` como coluna gerada (`loaned_on + 14`) e o índice único parcial `loan_one_open_per_copy` (um exemplar num só empréstimo aberto).

## Output de `invalid.sql`

```
ERROR:  new row for relation "copy" violates check constraint "copy_condition_check"
DETAIL:  Failing row contains (4, C-0099, 1, 2026-11-05, broken).
ERROR:  duplicate key value violates unique constraint "book_author_book_id_author_order_key"
DETAIL:  Key (book_id, author_order)=(2, 1) already exists.
ERROR:  duplicate key value violates unique constraint "loan_one_open_per_copy"
DETAIL:  Key (copy_id)=(3) already exists.
ERROR:  update or delete on table "publisher" violates RESTRICT setting of foreign key constraint "book_publisher_id_fkey" on table "book"
DETAIL:  Key (publisher_id)=(1) is referenced from table "book".
ERROR:  duplicate key value violates unique constraint "reader_email_key"
DETAIL:  Key (email)=(ana@mail.pt) already exists.
```

| # | Instrução | Constraint que a rejeita |
|---|---|---|
| 1 | `INSERT` de um exemplar com `condition = 'broken'` | `copy_condition_check` (CHECK) |
| 2 | `INSERT` de um 2.º autor na posição 1 do livro 2 | `book_author_book_id_author_order_key` (UNIQUE composto) |
| 3 | `INSERT` de um empréstimo de um exemplar que já está emprestado | `loan_one_open_per_copy` (índice único parcial) |
| 4 | `DELETE` de uma editora que ainda tem livros | `book_publisher_id_fkey` (FK com ON DELETE RESTRICT) |
| 5 | `INSERT` de um leitor com um email repetido | `reader_email_key` (UNIQUE) |
