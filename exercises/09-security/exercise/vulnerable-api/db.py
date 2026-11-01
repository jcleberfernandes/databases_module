from pathlib import Path

import psycopg
from dotenv import dotenv_values

# Usa POSTGRES_USER e POSTGRES_PASSWORD do .env da raiz do repositório
env = dotenv_values(Path(__file__).resolve().parents[4] / ".env")
URL = f"postgresql://{env['POSTGRES_USER']}:{env['POSTGRES_PASSWORD']}@localhost:5432/ex09"


def connect():
    return psycopg.connect(URL)
