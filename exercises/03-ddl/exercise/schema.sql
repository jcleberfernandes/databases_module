-- Exercício 03: biblioteca municipal (modelo do exercício 02)
-- Correr numa base vazia:
--   docker compose exec -T postgres psql -U postgres -d ex03 -v ON_ERROR_STOP=1 < exercises/03-ddl/exercise/schema.sql

DROP TABLE IF EXISTS fine, reservation, loan, copy, book_author, book, author, publisher, reader CASCADE;

CREATE TABLE publisher (
    publisher_id int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name         text NOT NULL UNIQUE
);

CREATE TABLE author (
    author_id int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name      text NOT NULL
);

CREATE TABLE book (
    book_id      int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    isbn         text NOT NULL UNIQUE,
    title        text NOT NULL,
    year         int CHECK (year BETWEEN 1450 AND 2100),
    -- RESTRICT: não se apaga uma editora que ainda tem livros
    publisher_id int NOT NULL REFERENCES publisher ON DELETE RESTRICT
);

CREATE TABLE book_author (
    -- CASCADE: se o livro for apagado, a ligação livro-autor deixa de fazer sentido
    book_id   int REFERENCES book ON DELETE CASCADE,
    author_id int REFERENCES author ON DELETE RESTRICT,
    PRIMARY KEY (book_id, author_id)
);

CREATE TABLE copy (
    copy_id int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    book_id int NOT NULL REFERENCES book ON DELETE RESTRICT,
    barcode text NOT NULL UNIQUE,
    status  text NOT NULL DEFAULT 'available'
            CHECK (status IN ('available', 'loaned', 'lost'))
);

CREATE TABLE reader (
    reader_id int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name      text NOT NULL,
    email     text NOT NULL UNIQUE CHECK (email LIKE '%@%'),
    joined_at date NOT NULL DEFAULT current_date
);

CREATE TABLE loan (
    loan_id     int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    -- RESTRICT: o histórico de empréstimos não pode desaparecer
    copy_id     int NOT NULL REFERENCES copy ON DELETE RESTRICT,
    reader_id   int NOT NULL REFERENCES reader ON DELETE RESTRICT,
    loaned_at   date NOT NULL DEFAULT current_date,
    due_at      date NOT NULL,
    returned_at date,
    CHECK (due_at > loaned_at),
    CHECK (returned_at IS NULL OR returned_at >= loaned_at)
);

CREATE TABLE reservation (
    reservation_id int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    book_id        int NOT NULL REFERENCES book ON DELETE CASCADE,
    -- CASCADE: se o leitor sai, as reservas dele deixam de existir
    reader_id      int NOT NULL REFERENCES reader ON DELETE CASCADE,
    reserved_at    timestamptz NOT NULL DEFAULT now(),
    status         text NOT NULL DEFAULT 'waiting'
                   CHECK (status IN ('waiting', 'ready', 'done', 'cancelled')),
    -- UNIQUE composto: um leitor só reserva o mesmo livro uma vez no mesmo instante
    UNIQUE (book_id, reader_id, reserved_at)
);

CREATE TABLE fine (
    fine_id int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    loan_id int NOT NULL UNIQUE REFERENCES loan ON DELETE RESTRICT,
    amount  numeric(6,2) NOT NULL CHECK (amount > 0),
    paid    boolean NOT NULL DEFAULT false
);

-- Dados de exemplo
INSERT INTO publisher (name) VALUES ('Porto Editora'), ('Leya');
INSERT INTO author (name) VALUES ('José Saramago'), ('Sophia de Mello Breyner');
INSERT INTO book (isbn, title, year, publisher_id) VALUES
    ('9789720046710', 'Ensaio sobre a Cegueira', 1995, 1),
    ('9789722035224', 'A Menina do Mar', 1958, 2);
INSERT INTO book_author VALUES (1, 1), (2, 2);
INSERT INTO copy (book_id, barcode) VALUES (1, 'C-0001'), (1, 'C-0002'), (2, 'C-0003');
INSERT INTO reader (name, email) VALUES ('Ana', 'ana@mail.pt'), ('Rui', 'rui@mail.pt');
INSERT INTO loan (copy_id, reader_id, loaned_at, due_at) VALUES (1, 1, '2026-10-01', '2026-10-15');
INSERT INTO reservation (book_id, reader_id, reserved_at) VALUES (1, 2, '2026-10-02 10:00');
INSERT INTO fine (loan_id, amount) VALUES (1, 2.50);
