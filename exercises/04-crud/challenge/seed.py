"""Adiciona 1 milhão de alugueres ao Pagila com COPY.

    uv run python seed.py ex04_seed_a

A ligação usa o .env da raiz do repositório (POSTGRES_USER e POSTGRES_PASSWORD).
"""

import random
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg
from dotenv import dotenv_values

ROWS = 1_000_000
FIRST_ID = 1_000_001  # ids reservados para o seed: assim sabemos o que já foi inserido
START = datetime(2023, 1, 1, tzinfo=timezone.utc)
LAST_UPDATE = "2026-01-01 00:00:00+00"

env = dotenv_values(Path(__file__).resolve().parents[3] / ".env")
db = sys.argv[1] if len(sys.argv) > 1 else "ex04"
url = f"postgresql://{env['POSTGRES_USER']}:{env['POSTGRES_PASSWORD']}@localhost:5432/{db}"


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
    "CREATE UNIQUE INDEX idx_unq_rental_rental_date_inventory_id_customer_id"
    " ON rental (rental_date, inventory_id, customer_id)",
    "CREATE UNIQUE INDEX rental_uuid_key ON rental (uuid)",
    "ALTER TABLE rental ADD CONSTRAINT rental_customer_id_fkey FOREIGN KEY (customer_id)"
    " REFERENCES customer (customer_id) ON UPDATE CASCADE ON DELETE RESTRICT",
    "ALTER TABLE rental ADD CONSTRAINT rental_inventory_id_fkey FOREIGN KEY (inventory_id)"
    " REFERENCES inventory (inventory_id) ON UPDATE CASCADE ON DELETE RESTRICT",
    "ALTER TABLE rental ADD CONSTRAINT rental_staff_id_fkey FOREIGN KEY (staff_id)"
    " REFERENCES staff (staff_id) ON UPDATE CASCADE ON DELETE RESTRICT",
]


def make_rows(inventory, customers, staff):
    rnd = random.Random(42)  # semente fixa = mesmos dados em todas as execuções
    for i in range(ROWS):
        # +1 minuto por linha: (rental_date, inventory_id, customer_id) nunca se repete
        rented = START + timedelta(minutes=i)
        returned = rented + timedelta(hours=rnd.randint(1, 240))  # sempre depois do aluguer
        yield (f"{FIRST_ID + i}\t{rented.isoformat()}\t{rnd.choice(inventory)}\t{rnd.choice(customers)}"
               f"\t{returned.isoformat()}\t{rnd.choice(staff)}\t{LAST_UPDATE}\n")


started = time.perf_counter()
with psycopg.connect(url) as conn:
    done = conn.execute("SELECT count(*) FROM rental WHERE rental_id >= %s", (FIRST_ID,)).fetchone()[0]
    if done == ROWS:
        print("Os dados já existem, nada a fazer.")
        sys.exit(0)
    # Se uma execução anterior ficou a meio, apaga e começa de novo
    conn.execute("DELETE FROM rental WHERE rental_id >= %s", (FIRST_ID,))

    # Só ids que existem, ordenados para o resultado ser sempre igual
    inventory = [r[0] for r in conn.execute("SELECT inventory_id FROM inventory ORDER BY 1")]
    customers = [r[0] for r in conn.execute("SELECT customer_id FROM customer ORDER BY 1")]
    staff = [r[0] for r in conn.execute("SELECT staff_id FROM staff ORDER BY 1")]

    # COPY para uma tabela temporária (sem índices nem FKs) é muito rápido...
    conn.execute("CREATE TEMP TABLE rental_seed (LIKE rental INCLUDING DEFAULTS) ON COMMIT DROP")
    with conn.cursor().copy(
        "COPY rental_seed (rental_id, rental_date, inventory_id, customer_id, return_date, staff_id, last_update)"
        " FROM STDIN"
    ) as copy:
        batch = []
        for line in make_rows(inventory, customers, staff):
            batch.append(line)
            if len(batch) == 10_000:
                copy.write("".join(batch))
                batch = []
        copy.write("".join(batch))
    print(f"COPY: {time.perf_counter() - started:.1f} s")

    # ...e depois um único INSERT ... SELECT passa tudo para rental.
    # Truque clássico de carga em massa: tirar FKs e índices secundários, inserir, e voltar a criá-los.
    # Recriar um índice ou validar uma FK de uma vez é muito mais rápido do que fazê-lo linha a linha.
    # Tudo na mesma transação: se algo falhar, nada muda.
    for sql in DROP:
        conn.execute(sql)
    conn.execute("INSERT INTO rental SELECT * FROM rental_seed")
    print(f"INSERT: {time.perf_counter() - started:.1f} s")
    for sql in CREATE:
        conn.execute(sql)  # ADD CONSTRAINT ... FOREIGN KEY verifica todas as linhas: dados inválidos dão erro
    conn.commit()
print(f"{ROWS:,} alugueres inseridos em {time.perf_counter() - started:.1f} s")
