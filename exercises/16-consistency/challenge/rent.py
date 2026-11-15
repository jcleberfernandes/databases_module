"""Insere N alugueres novos (clientes e cópias ao acaso). Cada aluguer e a sua linha de outbox
entram na MESMA transação: ou ficam os dois, ou nenhum.

    uv run python rent.py 5000
"""

import random
import sys
import time
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "exercise"))
from config import DATABASE_URL  # noqa: E402  (a configuração do exercício)

n = int(sys.argv[1])
started = time.perf_counter()
with psycopg.connect(DATABASE_URL) as conn:
    customers = [r[0] for r in conn.execute("SELECT customer_id FROM customer")]
    copies = conn.execute("SELECT inventory_id, film_id FROM inventory").fetchall()
    staff = [r[0] for r in conn.execute("SELECT staff_id FROM staff")]
    conn.commit()

    for i in range(1, n + 1):
        customer_id = random.choice(customers)
        inventory_id, film_id = random.choice(copies)
        with conn.transaction():
            conn.execute(
                "INSERT INTO rental (rental_date, inventory_id, customer_id, staff_id)"
                " VALUES (clock_timestamp(), %s, %s, %s)",
                (inventory_id, customer_id, random.choice(staff)),
            )
            conn.execute("INSERT INTO outbox (customer_id, film_id) VALUES (%s, %s)", (customer_id, film_id))
        if i % 1000 == 0:
            print(f"rent: {i} alugueres", flush=True)
print(f"rent: {n} alugueres + {n} linhas de outbox em {time.perf_counter() - started:.1f} s", flush=True)
