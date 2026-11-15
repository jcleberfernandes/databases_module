import os
from pathlib import Path

from dotenv import dotenv_values, load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()  # .env deste projeto, se existir


def database_url() -> str:
    if "DATABASE_URL" in os.environ:
        return os.environ["DATABASE_URL"]
    # Sem DATABASE_URL: usa POSTGRES_USER e POSTGRES_PASSWORD do .env da raiz do repositório
    root = dotenv_values(Path(__file__).resolve().parents[4] / ".env")
    return f"postgresql+psycopg://{root['POSTGRES_USER']}:{root['POSTGRES_PASSWORD']}@localhost:5432/ex12"


DATABASE_URL = database_url()
# echo=True escreve cada SQL no log: é assim que se contam as queries de cada pedido
engine = create_engine(DATABASE_URL, echo=os.getenv("SQL_ECHO", "true").lower() == "true")
SessionLocal = sessionmaker(engine)


def get_session():
    """Dependência do FastAPI: uma sessão por pedido, fechada no fim."""
    with SessionLocal() as session:
        yield session
