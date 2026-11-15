"""Versão 1 da API: usa a coluna email.

    uv run uvicorn api_v1:app --port 8001
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from db import engine

app = FastAPI(title="Clientes v1 (email)")


class NewEmail(BaseModel):
    email: str


@app.get("/customers/{customer_id}")
def get_customer(customer_id: int):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT customer_id, first_name, last_name, email FROM customer WHERE customer_id = :id"),
            {"id": customer_id},
        ).mappings().one_or_none()
    if row is None:
        raise HTTPException(404, "Customer not found")
    return dict(row)


@app.put("/customers/{customer_id}/email")
def change_email(customer_id: int, body: NewEmail):
    with engine.begin() as conn:
        changed = conn.execute(
            text("UPDATE customer SET email = :email WHERE customer_id = :id"),
            {"email": body.email, "id": customer_id},
        ).rowcount
    if changed == 0:
        raise HTTPException(404, "Customer not found")
    return get_customer(customer_id)
