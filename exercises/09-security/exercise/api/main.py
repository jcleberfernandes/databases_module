"""Exercício 09: 3 endpoints, cada um escreve num motor com o utilizador de menos privilégios.

    uv run uvicorn main:app --port 8009

As credenciais vêm de variáveis de ambiente (DATABASE_URL, MONGO_URL, REDIS_URL), nunca do código.
"""

import os

import psycopg
import redis
from dotenv import load_dotenv
from fastapi import FastAPI, Path
from pydantic import BaseModel, StrictInt, StrictStr
from pymongo import MongoClient

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

DATABASE_URL = os.environ["DATABASE_URL"]
mongo_db = MongoClient(os.environ["MONGO_URL"]).get_default_database()  # a base ex09 do URL
r = redis.Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)

app = FastAPI(title="Exercício 09")


class NewActor(BaseModel):
    first_name: StrictStr
    last_name: StrictStr


class NewNote(BaseModel):
    # Strict: "1" ou {"$ne": null} não são convertidos; qualquer outro tipo dá 422
    customer_id: StrictInt
    text: StrictStr


@app.post("/actors", status_code=201)
def create_actor(body: NewActor):
    with psycopg.connect(DATABASE_URL) as conn:
        # parâmetros (%s): o texto é enviado como valor, nunca faz parte do SQL
        actor_id = conn.execute(
            "INSERT INTO actor (first_name, last_name) VALUES (%s, %s) RETURNING actor_id",
            (body.first_name, body.last_name),
        ).fetchone()[0]
    return {"actor_id": actor_id}


@app.post("/notes", status_code=201)
def create_note(body: NewNote):
    result = mongo_db.notes.insert_one({"customer_id": body.customer_id, "text": body.text})
    return {"_id": str(result.inserted_id)}


@app.post("/counters/{name}")
def increment_counter(name: str = Path(pattern=r"^[a-z0-9_-]{1,32}$")):
    # o nome já foi validado: só letras minúsculas, números, _ e -
    # INCR à letra (r.incr() do redis-py envia INCRBY, que o utilizador ACL não pode correr)
    return {"name": name, "value": r.execute_command("INCR", f"counter:{name}")}
