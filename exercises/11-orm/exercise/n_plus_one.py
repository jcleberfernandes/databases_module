"""Ponto 3: N+1 de propósito (filmes e os seus atores), contar as queries, corrigir e contar outra vez.

    uv run python n_plus_one.py
"""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from db import count_queries, engine
from models import Film

LIMIT = 50


def lazy():
    # N+1: 1 query para os filmes + 1 query por filme quando se lê film.actors
    with Session(engine) as session, count_queries() as statements:
        films = session.scalars(select(Film).order_by(Film.film_id).limit(LIMIT)).all()
        for f in films:
            names = ", ".join(a.last_name for a in f.actors)
    print(f"último: {f.title}: {names}")
    return statements


def eager():
    # Corrigido: selectinload carrega os atores de todos os filmes numa 2.ª query (WHERE film_id IN (...))
    with Session(engine) as session, count_queries() as statements:
        stmt = select(Film).options(selectinload(Film.actors)).order_by(Film.film_id).limit(LIMIT)
        films = session.scalars(stmt).all()
        for f in films:
            names = ", ".join(a.last_name for a in f.actors)
    print(f"último: {f.title}: {names}")
    return statements


before = lazy()
print(f"ANTES  (lazy):        {len(before)} queries para {LIMIT} filmes")
print(f"  1.ª: {before[0].splitlines()[0]} ...")
print(f"  2.ª: {' '.join(before[1].split())}")
after = eager()
print(f"DEPOIS (selectinload): {len(after)} queries para {LIMIT} filmes")
for s in after:
    print(f"  {' '.join(s.split())[:160]}")
