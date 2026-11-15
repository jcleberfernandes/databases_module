-- 5 instruções que têm de falhar, cada uma por uma constraint diferente (correr depois de schema.sql)
-- docker compose exec -T postgres psql -U postgres -d ex03 < exercises/03-ddl/exercise/invalid.sql

-- copy_condition_check: 'broken' não é um estado válido de um exemplar
INSERT INTO copy (barcode, book_id, condition) VALUES ('C-0099', 1, 'broken');

-- book_author_book_id_author_order_key: o livro 2 já tem um autor na posição 1
INSERT INTO book_author (book_id, author_id, author_order) VALUES (2, 1, 1);

-- loan_one_open_per_copy: o exemplar 3 já está num empréstimo aberto
INSERT INTO loan (reader_id, copy_id) VALUES (1, 3);

-- book_publisher_id_fkey (ON DELETE RESTRICT): a editora 1 ainda tem livros
DELETE FROM publisher WHERE publisher_id = 1;

-- reader_email_key: já existe um leitor com este email
INSERT INTO reader (card_number, name, email, phone, address) VALUES ('L-1003', 'Outra Ana', 'ana@mail.pt', '910000003', 'Rua C');
