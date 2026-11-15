"""Challenge 09: a API do exercício, com leituras, a correr em duas instâncias.

    uv run --env-file ../.env.a uvicorn main:app --port 8001    # utilizadores do exercício
    uv run --env-file ../.env.b uvicorn main:app --port 8002    # utilizadores só de leitura

O código é o mesmo nas duas: só as variáveis de ambiente mudam. Não há nenhum "if instância B":
os 403 vêm dos erros de privilégio que os próprios motores devolvem.
"""

import os

import psycopg
import redis
from fastapi import FastAPI, HTTPException, Path, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, StrictInt, StrictStr
from pymongo import MongoClient
from pymongo.errors import OperationFailure

DATABASE_URL = os.environ["DATABASE_URL"]
mongo_db = MongoClient(os.environ["MONGO_URL"]).get_default_database()
r = redis.Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)

app = FastAPI(title="Challenge 09")
COUNTER_NAME = r"^[a-z0-9_-]{1,32}$"


# ---------- 403 só quando o motor recusa por falta de privilégio; qualquer outro erro fica 500
@app.exception_handler(psycopg.errors.InsufficientPrivilege)   # SQLSTATE 42501
async def pg_forbidden(request: Request, exc):
    return JSONResponse(status_code=403, content={"detail": f"PostgreSQL: {exc.diag.message_primary}"})


@app.exception_handler(OperationFailure)
async def mongo_forbidden(request: Request, exc: OperationFailure):
    if exc.code == 13:  # Unauthorized
        return JSONResponse(status_code=403, content={"detail": f"MongoDB: {exc.details.get('errmsg')}"})
    raise exc


@app.exception_handler(redis.exceptions.NoPermissionError)     # NOPERM
async def redis_forbidden(request: Request, exc):
    return JSONResponse(status_code=403, content={"detail": f"Redis: {exc}"})


class NewActor(BaseModel):
    first_name: StrictStr
    last_name: StrictStr


class NewNote(BaseModel):
    customer_id: StrictInt
    text: StrictStr


# ---------- escritas (do exercício)
@app.post("/actors", status_code=201)
def create_actor(body: NewActor):
    with psycopg.connect(DATABASE_URL) as conn:
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
def increment_counter(name: str = Path(pattern=COUNTER_NAME)):
    return {"name": name, "value": r.execute_command("INCR", f"counter:{name}")}


# ---------- leituras (novas)
@app.get("/actors/{actor_id}")
def get_actor(actor_id: int):
    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute("SELECT actor_id, first_name, last_name FROM actor WHERE actor_id = %s",
                           (actor_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Actor not found")
    return {"actor_id": row[0], "first_name": row[1], "last_name": row[2]}


@app.get("/notes")
def get_notes(customer_id: int):
    return [{"customer_id": n["customer_id"], "text": n["text"]}
            for n in mongo_db.notes.find({"customer_id": customer_id})]


@app.get("/counters/{name}")
def get_counter(name: str = Path(pattern=COUNTER_NAME)):
    value = r.execute_command("GET", f"counter:{name}")
    return {"name": name, "value": int(value) if value is not None else 0}
