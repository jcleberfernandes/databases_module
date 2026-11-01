from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import create_engine, event

# Usa POSTGRES_USER e POSTGRES_PASSWORD do .env da raiz do repositório
env = dotenv_values(Path(__file__).resolve().parents[3] / ".env")
URL = f"postgresql+psycopg://{env['POSTGRES_USER']}:{env['POSTGRES_PASSWORD']}@localhost:5432/ex11"

engine = create_engine(URL)

# Contador de queries: cada SQL enviado à base passa por aqui
_statements: list[str] | None = None


@event.listens_for(engine, "before_cursor_execute")
def _count(conn, cursor, statement, parameters, context, executemany):
    if _statements is not None:
        _statements.append(statement)


@contextmanager
def count_queries() -> Iterator[list[str]]:
    """Guarda todos os SQL enviados dentro do bloco. len() dá o número de queries."""
    global _statements
    _statements = []
    try:
        yield _statements
    finally:
        _statements = None
