-- Exercício 03: a biblioteca municipal do exercício 02 em PostgreSQL
-- ./scripts/create-db.sh ex03
-- docker compose exec -T postgres psql -U postgres -d ex03 -v ON_ERROR_STOP=1 < exercises/03-ddl/exercise/schema.sql

DROP TABLE IF EXISTS fine, reservation, loan, copy, book_author, book, author, publisher, reader;

CREATE TABLE reader (
    reader_id     integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    card_number   text NOT NULL CONSTRAINT reader_card_number_key UNIQUE,
    name          text NOT NULL,
    email         text NOT NULL CONSTRAINT reader_email_key UNIQUE,
    phone         text NOT NULL,
    address       text NOT NULL,
    registered_on date NOT NULL DEFAULT current_date
);

CREATE TABLE publisher (
    publisher_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name         text NOT NULL CONSTRAINT publisher_name_key UNIQUE,
    country      text NOT NULL
);

CREATE TABLE author (
    author_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name      text NOT NULL
);

CREATE TABLE book (
    book_id          integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    isbn             text NOT NULL CONSTRAINT book_isbn_key UNIQUE,
    title            text NOT NULL,
    publication_year integer NOT NULL CONSTRAINT book_year_check CHECK (publication_year BETWEEN 1450 AND 2100),
    -- ON DELETE RESTRICT: não se pode apagar uma editora que ainda tem livros no catálogo;
    -- os livros ficavam sem editora (e cada livro tem de ter exatamente uma).
    publisher_id     integer NOT NULL
                     CONSTRAINT book_publisher_id_fkey REFERENCES publisher ON DELETE RESTRICT
);

CREATE TABLE book_author (
    -- ON DELETE CASCADE: a ligação livro–autor só existe por causa do livro;
    -- se o livro sai do catálogo, as suas linhas de autoria deixam de fazer sentido.
    book_id      integer NOT NULL CONSTRAINT book_author_book_id_fkey REFERENCES book ON DELETE CASCADE,
    author_id    integer NOT NULL CONSTRAINT book_author_author_id_fkey REFERENCES author ON DELETE RESTRICT,
    author_order integer NOT NULL CONSTRAINT book_author_order_check CHECK (author_order >= 1),
    PRIMARY KEY (book_id, author_id),
    -- UNIQUE composto: um livro não pode ter dois "primeiros autores"
    CONSTRAINT book_author_book_id_author_order_key UNIQUE (book_id, author_order)
);

CREATE TABLE copy (
    copy_id     integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    barcode     text NOT NULL CONSTRAINT copy_barcode_key UNIQUE,
    -- ON DELETE RESTRICT: não se apaga um livro que ainda tem exemplares na biblioteca
    book_id     integer NOT NULL CONSTRAINT copy_book_id_fkey REFERENCES book ON DELETE RESTRICT,
    acquired_on date NOT NULL DEFAULT current_date,
    condition   text NOT NULL DEFAULT 'new'
                CONSTRAINT copy_condition_check CHECK (condition IN ('new', 'good', 'worn', 'damaged'))
);

CREATE TABLE loan (
    loan_id     integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    -- ON DELETE RESTRICT: o histórico de empréstimos não pode desaparecer (multas, estatísticas)
    reader_id   integer NOT NULL CONSTRAINT loan_reader_id_fkey REFERENCES reader ON DELETE RESTRICT,
    copy_id     integer NOT NULL CONSTRAINT loan_copy_id_fkey REFERENCES copy ON DELETE RESTRICT,
    loaned_on   date NOT NULL DEFAULT current_date,
    due_on      date GENERATED ALWAYS AS (loaned_on + 14) STORED,   -- 14 dias depois do empréstimo
    returned_on date,                                               -- vazio até devolver
    CONSTRAINT loan_returned_check CHECK (returned_on IS NULL OR returned_on >= loaned_on)
);
-- Um exemplar está no máximo num empréstimo aberto
CREATE UNIQUE INDEX loan_one_open_per_copy ON loan (copy_id) WHERE returned_on IS NULL;

CREATE TABLE reservation (
    reservation_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    -- ON DELETE CASCADE: se o leitor deixa a biblioteca, as reservas dele deixam de existir
    reader_id      integer NOT NULL CONSTRAINT reservation_reader_id_fkey REFERENCES reader ON DELETE CASCADE,
    book_id        integer NOT NULL CONSTRAINT reservation_book_id_fkey REFERENCES book ON DELETE CASCADE,
    reserved_at    timestamptz NOT NULL DEFAULT now(),   -- as reservas são atendidas por esta ordem
    status         text NOT NULL DEFAULT 'active'
                   CONSTRAINT reservation_status_check CHECK (status IN ('active', 'fulfilled', 'cancelled'))
);

CREATE TABLE fine (
    fine_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    -- UNIQUE: uma multa pertence a exatamente um empréstimo, e um empréstimo tem no máximo uma multa
    loan_id integer NOT NULL CONSTRAINT fine_loan_id_key UNIQUE
            CONSTRAINT fine_loan_id_fkey REFERENCES loan ON DELETE RESTRICT,
    amount  numeric(8,2) NOT NULL CONSTRAINT fine_amount_check CHECK (amount > 0),
    paid_on date                                          -- vazio até pagar
);

-- Dados de exemplo
INSERT INTO publisher (name, country) VALUES ('Porto Editora', 'Portugal'), ('Leya', 'Portugal');
INSERT INTO author (name) VALUES ('José Saramago'), ('Sophia de Mello Breyner Andresen'), ('Miguel Torga');
INSERT INTO book (isbn, title, publication_year, publisher_id) VALUES
    ('9789720046710', 'Ensaio sobre a Cegueira', 1995, 1),
    ('9789722035224', 'A Menina do Mar', 1958, 2);
INSERT INTO book_author (book_id, author_id, author_order) VALUES (1, 1, 1), (2, 2, 1), (2, 3, 2);
INSERT INTO copy (barcode, book_id, acquired_on, condition) VALUES
    ('C-0001', 1, '2024-01-10', 'good'), ('C-0002', 1, '2024-01-10', 'new'), ('C-0003', 2, '2023-05-02', 'worn');
INSERT INTO reader (card_number, name, email, phone, address, registered_on) VALUES
    ('L-1001', 'Ana Silva', 'ana@mail.pt', '910000001', 'Rua A, Porto', '2025-09-01'),
    ('L-1002', 'Rui Costa', 'rui@mail.pt', '910000002', 'Rua B, Lisboa', '2025-09-15');
INSERT INTO loan (reader_id, copy_id, loaned_on, returned_on) VALUES (1, 1, '2026-10-01', '2026-10-20');
INSERT INTO loan (reader_id, copy_id, loaned_on) VALUES (2, 3, '2026-10-25');
INSERT INTO reservation (reader_id, book_id, reserved_at) VALUES (1, 2, '2026-10-26 10:00');
INSERT INTO fine (loan_id, amount) VALUES (1, 2.50);   -- 5 dias de atraso × 0.50
