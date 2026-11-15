import sys
from contextlib import contextmanager
from pathlib import Path

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from films import make_engine  # noqa: E402


@pytest.fixture(scope="session")
def engine():
    return make_engine(echo=False)


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s


@pytest.fixture
def query_counter(engine):
    """Lista com cada SQL que o engine corre (evento before_cursor_execute)."""
    statements = []

    def count(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", count)
    yield statements
    event.remove(engine, "before_cursor_execute", count)


@pytest.fixture
def assert_max_queries(query_counter):
    """with assert_max_queries(3): ...   falha se o bloco correr mais de 3 SQL."""

    @contextmanager
    def check(n):
        start = len(query_counter)
        yield
        ran = query_counter[start:]
        assert len(ran) <= n, f"{len(ran)} statements ran (max {n}):\n" + "\n".join(
            " ".join(s.split())[:120] for s in ran
        )

    return check
