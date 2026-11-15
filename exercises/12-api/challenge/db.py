import os
from pathlib import Path

from dotenv import dotenv_values, load_dotenv
from sqlalchemy import create_engine

load_dotenv()  # .env deste projeto, se existir


def database_url() -> str:
    if "DATABASE_URL" in os.environ:
        return os.environ["DATABASE_URL"]
    # Sem DATABASE_URL: usa POSTGRES_USER e POSTGRES_PASSWORD do .env da raiz do repositório
    root = dotenv_values(Path(__file__).resolve().parents[3] / ".env")
    return f"postgresql+psycopg://{root['POSTGRES_USER']}:{root['POSTGRES_PASSWORD']}@localhost:5432/ex12"


DATABASE_URL = database_url()
engine = create_engine(DATABASE_URL)
