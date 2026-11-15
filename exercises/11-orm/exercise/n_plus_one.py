"""Tarefa 3: um N+1 de propósito (os primeiros 100 filmes e os nomes dos atores através de
film.actors), contar os SELECT, corrigir com eager loading e contar outra vez, noutra sessão.

    uv run python n_plus_one.py
"""

from sqlalchemy import event, select
from sqlalchemy.orm import Session, selectinload

from models import Film, make_engine

engine = make_engine(echo=False)  # aqui interessa a contagem; o queries.py mostra o SQL
statements: list[str] = []


@event.listens_for(engine, "before_cursor_execute")
def count(conn, cursor, statement, parameters, context, executemany):
    statements.append(statement)


def list_films(eager: bool) -> int:
    statements.clear()
    with Session(engine) as session:  # uma sessão nova: nada vem já carregado da anterior
        stmt = select(Film).order_by(Film.film_id).limit(100)
        if eager:
            stmt = stmt.options(selectinload(Film.actors))
        for film in session.scalars(stmt):
            names = ", ".join(f"{a.first_name} {a.last_name}" for a in film.actors)
            last = f"{film.title}: {names}"
    print(f"   último: {last}")
    return sum(1 for s in statements if s.lstrip().upper().startswith("SELECT"))


print("ANTES (lazy loading):")
before = list_films(eager=False)
print(f"   {before} SELECT para 100 filmes")
print("DEPOIS (selectinload):")
after = list_films(eager=True)
print(f"   {after} SELECT para 100 filmes")
for s in statements:
    print("   " + " ".join(s.split())[:150])
