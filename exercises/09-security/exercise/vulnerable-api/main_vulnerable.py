"""VERSÃO VULNERÁVEL (original). Não usar.

    uv run uvicorn main_vulnerable:app --port 8009
"""

from fastapi import FastAPI

from db import connect

app = FastAPI(title="Exercício 09: API vulnerável")


@app.get("/customers")
def find_customer(email: str):
    with connect() as conn:
        # VULNERÁVEL: o texto do utilizador é colado dentro do SQL
        rows = conn.execute(
            f"SELECT customer_id, first_name, last_name, email FROM customer WHERE email = '{email}'"
        ).fetchall()
    return [{"id": r[0], "first_name": r[1], "last_name": r[2], "email": r[3]} for r in rows]
