import sys
from pathlib import Path

import psycopg
from dotenv import dotenv_values

# Usa POSTGRES_USER e POSTGRES_PASSWORD do .env da raiz do repositório
env = dotenv_values(Path(__file__).resolve().parents[3] / ".env")
DB = sys.argv[1] if len(sys.argv) > 1 else "ex08"
URL = f"postgresql://{env['POSTGRES_USER']}:{env['POSTGRES_PASSWORD']}@localhost:5432/{DB}"


def connect(**kwargs):
    return psycopg.connect(URL, **kwargs)
