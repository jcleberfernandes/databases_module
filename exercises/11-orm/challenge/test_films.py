"""Listar 100 filmes com atores e categorias tem de fazer no máximo 3 queries.

    uv run pytest -v
"""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from models import Film


def list_films(session, eager=True):
    stmt = select(Film).order_by(Film.film_id).limit(100)
    if eager:
        stmt = stmt.options(selectinload(Film.actors), selectinload(Film.categories))
    return [
        {
            "title": f.title,
            "actors": [a.last_name for a in f.actors],
            "categories": [c.name for c in f.categories],
        }
        for f in session.scalars(stmt)
    ]


def test_list_100_films_with_actors_and_categories(session, assert_max_queries):
    with assert_max_queries(3):
        films = list_films(session)
    assert len(films) == 100
    assert all(f["categories"] for f in films)


def test_counter_counts_queries(session, query_counter):
    list_films(session)
    assert len(query_counter) == 3  # filmes + atores + categorias


@pytest.mark.xfail(strict=True, reason="N+1 de propósito: o teste TEM de falhar")
def test_n_plus_one_is_caught(session, assert_max_queries):
    with assert_max_queries(3):
        list_films(session, eager=False)
