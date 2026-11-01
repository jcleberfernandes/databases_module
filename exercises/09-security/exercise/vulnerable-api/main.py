"""VERSÃO CORRIGIDA.

    uv run uvicorn main:app --port 8009
"""

from fastapi import FastAPI

from db import connect

app = FastAPI(title="Exercício 09: API corrigida")


@app.get("/customers")
def find_customer(email: str):
    with connect() as conn:
        # SEGURO: o email é enviado como valor (%s), nunca faz parte do SQL
        rows = conn.execute(
            "SELECT customer_id, first_name, last_name, email FROM customer WHERE email = %s",
            (email,),
        ).fetchall()
    return [{"id": r[0], "first_name": r[1], "last_name": r[2], "email": r[3]} for r in rows]
