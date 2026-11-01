import sys
from contextlib import contextmanager
from pathlib import Path

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

# Reutiliza o engine e os modelos do exercício
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "exercise"))
from db import engine  # noqa: E402


@pytest.fixture
def session():
    with Session(engine) as s:
        yield s


@pytest.fixture
def query_counter():
    """Conta os SQL enviados à base com o evento before_cursor_execute."""
    statements = []

    def count(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", count)
    yield statements
    event.remove(engine, "before_cursor_execute", count)


@pytest.fixture
def assert_max_queries(query_counter):
    """Uso:  with assert_max_queries(3): ...   falha se o bloco fizer mais de 3 queries."""

    @contextmanager
    def check(n):
        start = len(query_counter)
        yield
        made = query_counter[start:]
        assert len(made) <= n, f"{len(made)} queries (máximo {n}):\n" + "\n".join(
            " ".join(s.split())[:120] for s in made
        )

    return check
