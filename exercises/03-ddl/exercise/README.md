# Exercício 03 — DDL

Ficheiros: `schema.sql` (modelo da biblioteca) e `invalid.sql` (5 INSERTs que falham).

```bash
./scripts/create-db.sh ex03
docker compose exec -T postgres psql -U postgres -d ex03 -v ON_ERROR_STOP=1 < exercises/03-ddl/exercise/schema.sql
docker compose exec -T postgres psql -U postgres -d ex03 < exercises/03-ddl/exercise/invalid.sql
```

Resultado do `invalid.sql`:

```
ERROR:  new row for relation "book" violates check constraint "book_year_check"
ERROR:  duplicate key value violates unique constraint "book_isbn_key"
ERROR:  insert or update on table "loan" violates foreign key constraint "loan_reader_id_fkey"
ERROR:  duplicate key value violates unique constraint "reservation_book_id_reader_id_reserved_at_key"
ERROR:  new row for relation "loan" violates check constraint "loan_check"
```
