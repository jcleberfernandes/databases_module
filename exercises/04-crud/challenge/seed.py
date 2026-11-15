"""Adiciona 1 000 000 de alugueres ao Pagila com COPY.

    uv run python seed.py ch04_a

- rental_id de 100 001 a 1 100 000 (iguais em todas as execuções); no fim, setval da sequência.
- inventory_id, customer_id e staff_id escolhidos entre os que existem.
- rental_date entre 2022-01-01 e 2026-07-31; return_date NULL ou depois de rental_date.
- semente fixa: as duas bases ficam com as mesmas linhas.
- idempotente: se as 1 000 000 linhas já existem, não faz nada.
"""

import os
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg
from dotenv import dotenv_values, load_dotenv

load_dotenv()
_root = dotenv_values(Path(__file__).resolve().parents[3] / ".env")
POSTGRES_URL = os.environ.get("POSTGRES_URL") or (
    f"postgresql://{_root['POSTGRES_USER']}:{_root['POSTGRES_PASSWORD']}@localhost:5432"
)

ROWS = 1_000_000
FIRST_ID, LAST_ID = 100_001, 1_100_000
START = datetime(2022, 1, 1, tzinfo=timezone.utc)
END = datetime(2026, 7, 31, tzinfo=timezone.utc)
SECONDS = int((END - START).total_seconds())

# Para carregar depressa: tirar as FKs e os índices secundários, inserir, voltar a criá-los.
# Recriar um índice ou validar uma FK de uma vez é muito mais rápido do que linha a linha.
DROP = [
    "ALTER TABLE rental DROP CONSTRAINT rental_customer_id_fkey",
    "ALTER TABLE rental DROP CONSTRAINT rental_inventory_id_fkey",
    "ALTER TABLE rental DROP CONSTRAINT rental_staff_id_fkey",
    "DROP INDEX idx_fk_inventory_id",
    "DROP INDEX idx_unq_rental_rental_date_inventory_id_customer_id",
    "DROP INDEX rental_uuid_key",
]
CREATE = [
    "CREATE INDEX idx_fk_inventory_id ON rental (inventory_id)",
    # o índice único volta a ser criado: se houvesse uma linha repetida, dava erro aqui
    "CREATE UNIQUE INDEX idx_unq_rental_rental_date_inventory_id_customer_id"
    " ON rental (rental_date, inventory_id, customer_id)",
    "CREATE UNIQUE INDEX rental_uuid_key ON rental (uuid)",
    # ADD CONSTRAINT ... FOREIGN KEY verifica todas as linhas: um id que não existisse dava erro
    "ALTER TABLE rental ADD CONSTRAINT rental_customer_id_fkey FOREIGN KEY (customer_id)"
    " REFERENCES customer (customer_id) ON UPDATE CASCADE ON DELETE RESTRICT",
    "ALTER TABLE rental ADD CONSTRAINT rental_inventory_id_fkey FOREIGN KEY (inventory_id)"
    " REFERENCES inventory (inventory_id) ON UPDATE CASCADE ON DELETE RESTRICT",
    "ALTER TABLE rental ADD CONSTRAINT rental_staff_id_fkey FOREIGN KEY (staff_id)"
    " REFERENCES staff (staff_id) ON UPDATE CASCADE ON DELETE RESTRICT",
]


def make_rows(inventory, customers, staff):
    rnd = random.Random(42)  # semente fixa
    # segundos todos diferentes entre si; o ,500000 (meio segundo) evita coincidir com os
    # alugueres que o Pagila já tem: assim o índice único nunca é violado
    offsets = sorted(rnd.sample(range(SECONDS), ROWS))
    for i, offset in enumerate(offsets):
        rented = START + timedelta(seconds=offset, microseconds=500_000)
        if rnd.random() < 0.02:
            returned = r"\N"  # NULL no COPY: ainda não devolvido
        else:
            returned = (rented + timedelta(hours=rnd.randint(1, 240))).isoformat()
        yield (f"{FIRST_ID + i}\t{rented.isoformat()}\t{rnd.choice(inventory)}\t"
               f"{rnd.choice(customers)}\t{returned}\t{rnd.choice(staff)}\n")


db = sys.argv[1]
started = time.perf_counter()
with psycopg.connect(f"{POSTGRES_URL}/{db}") as conn:
    done = conn.execute("SELECT count(*) FROM rental WHERE rental_id BETWEEN %s AND %s",
                        (FIRST_ID, LAST_ID)).fetchone()[0]
    if done == ROWS:
        print(f"{db}: as {ROWS:,} linhas já existem, nada a fazer")
        sys.exit(0)
    # se uma execução anterior ficou a meio, apaga e recomeça
    conn.execute("DELETE FROM rental WHERE rental_id BETWEEN %s AND %s", (FIRST_ID, LAST_ID))

    inventory = [r[0] for r in conn.execute("SELECT inventory_id FROM inventory ORDER BY 1")]
    customers = [r[0] for r in conn.execute("SELECT customer_id FROM customer ORDER BY 1")]
    staff = [r[0] for r in conn.execute("SELECT staff_id FROM staff ORDER BY 1")]

    # COPY para uma tabela temporária (sem índices nem FKs)...
    conn.execute("CREATE TEMP TABLE rental_seed (LIKE rental INCLUDING DEFAULTS) ON COMMIT DROP")
    with conn.cursor().copy(
        "COPY rental_seed (rental_id, rental_date, inventory_id, customer_id, return_date, staff_id) FROM STDIN"
    ) as copy:
        batch = []
        for line in make_rows(inventory, customers, staff):
            batch.append(line)
            if len(batch) == 10_000:
                copy.write("".join(batch))
                batch = []
        copy.write("".join(batch))

    # ...e um só INSERT ... SELECT para rental, tudo na mesma transação
    for sql in DROP:
        conn.execute(sql)
    conn.execute("INSERT INTO rental SELECT * FROM rental_seed")
    for sql in CREATE:
        conn.execute(sql)
    conn.execute("SELECT setval('rental_rental_id_seq', (SELECT max(rental_id) FROM rental))")
    conn.commit()
print(f"{db}: {ROWS:,} alugueres inseridos em {time.perf_counter() - started:.1f} s")
