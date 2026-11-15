"""O código testado: lista filmes com os atores e as categorias.
Usa os modelos do exercício (../exercise/models.py)."""

import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "exercise"))
from models import Film, make_engine  # noqa: E402,F401  (make_engine é usado pelos testes)


def list_films(session: Session, limit: int = 100) -> list[dict]:
    stmt = (
        select(Film)
        .order_by(Film.film_id)
        .limit(limit)
        .options(selectinload(Film.actors), selectinload(Film.categories))  # eager loading
    )
    return [
        {
            "title": f.title,
            "actors": [f"{a.first_name} {a.last_name}" for a in f.actors],
            "categories": [c.name for c in f.categories],
        }
        for f in session.scalars(stmt)
    ]

