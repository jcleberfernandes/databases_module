-- 5 INSERTs que têm de falhar (correr depois de schema.sql).
-- Sem ON_ERROR_STOP, para ver os 5 erros:
--   docker compose exec -T postgres psql -U postgres -d ex03 < exercises/03-ddl/exercise/invalid.sql

-- 1. CHECK book_year_check: ano fora do intervalo
INSERT INTO book (isbn, title, year, publisher_id) VALUES ('9780000000001', 'Futuro', 3000, 1);

-- 2. UNIQUE book_isbn_key: ISBN repetido
INSERT INTO book (isbn, title, year, publisher_id) VALUES ('9789720046710', 'Cópia', 2000, 1);

-- 3. FOREIGN KEY loan_reader_id_fkey: leitor 999 não existe
INSERT INTO loan (copy_id, reader_id, due_at) VALUES (2, 999, current_date + 14);

-- 4. UNIQUE composto reservation_book_id_reader_id_reserved_at_key: reserva repetida
INSERT INTO reservation (book_id, reader_id, reserved_at) VALUES (1, 2, '2026-10-02 10:00');

-- 5. CHECK loan_check: data de entrega antes da data do empréstimo
INSERT INTO loan (copy_id, reader_id, loaned_at, due_at) VALUES (2, 1, '2026-10-10', '2026-10-01');
