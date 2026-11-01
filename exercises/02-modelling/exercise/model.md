# Exercício 02 — Modelo da biblioteca municipal

## 1. Diagrama ER

```mermaid
erDiagram
    PUBLISHER ||--o{ BOOK : publica
    BOOK ||--o{ BOOK_AUTHOR : tem
    AUTHOR ||--o{ BOOK_AUTHOR : escreve
    BOOK ||--o{ COPY : "tem exemplares"
    READER ||--o{ LOAN : faz
    COPY ||--o{ LOAN : "é emprestado em"
    READER ||--o{ RESERVATION : faz
    BOOK ||--o{ RESERVATION : "é reservado em"
    LOAN ||--o| FINE : gera

    PUBLISHER {
        int publisher_id PK
        text name
    }
    AUTHOR {
        int author_id PK
        text name
    }
    BOOK {
        int book_id PK
        text isbn UK
        text title
        int year
        int publisher_id FK
    }
    BOOK_AUTHOR {
        int book_id PK,FK
        int author_id PK,FK
    }
    COPY {
        int copy_id PK
        int book_id FK
        text barcode UK
        text status
    }
    READER {
        int reader_id PK
        text name
        text email UK
        date joined_at
    }
    LOAN {
        int loan_id PK
        int copy_id FK
        int reader_id FK
        date loaned_at
        date due_at
        date returned_at
    }
    RESERVATION {
        int reservation_id PK
        int book_id FK
        int reader_id FK
        timestamp reserved_at
        text status
    }
    FINE {
        int fine_id PK
        int loan_id FK,UK
        numeric amount
        boolean paid
    }
```

## 2. Tabelas (3NF)

| Tabela | PK | FK |
|---|---|---|
| publisher | publisher_id | — |
| author | author_id | — |
| book | book_id | publisher_id → publisher |
| book_author | (book_id, author_id) | book_id → book, author_id → author |
| copy | copy_id | book_id → book |
| reader | reader_id | — |
| loan | loan_id | copy_id → copy, reader_id → reader |
| reservation | reservation_id | book_id → book, reader_id → reader |
| fine | fine_id | loan_id → loan (único: no máximo 1 multa por empréstimo) |

## 3. Desnormalização

Nenhuma. O volume de uma biblioteca é pequeno e as consultas (ex: "livros
emprestados de um leitor") são joins simples e rápidos com índices nas FKs.
O valor da multa é guardado em `fine.amount` porque é um valor histórico
(o preço por dia pode mudar), não um cálculo duplicado.
