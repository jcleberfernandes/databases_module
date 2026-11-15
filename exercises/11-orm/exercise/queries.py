"""Tarefa 2: as 3 queries com o ORM (echo=True mostra o SQL gerado) e o mesmo resultado
que o SQL escrito à mão.

    uv run python queries.py
"""

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from models import Actor, Category, Film, film_actor, film_category, make_engine

engine = make_engine(echo=True)

# Q1: número de filmes por categoria, mais filmes primeiro
films = func.count().label("films")
q1 = (
    select(Category.name, films)
    .join(film_category, film_category.c.category_id == Category.category_id)
    .group_by(Category.category_id, Category.name)
    .order_by(films.desc(), Category.name)
)
q1_sql = """SELECT c.name, count(*) AS films
FROM category c JOIN film_category fc ON fc.category_id = c.category_id
GROUP BY c.category_id, c.name
ORDER BY films DESC, c.name"""

# Q2: filmes mais longos do que o filme médio
q2 = (
    select(Film.film_id, Film.title, Film.length)
    .where(Film.length > select(func.avg(Film.length)).scalar_subquery())
    .order_by(Film.length.desc(), Film.film_id)
)
q2_sql = """SELECT f.film_id, f.title, f.length
FROM film f
WHERE f.length > (SELECT avg(length) FROM film)
ORDER BY f.length DESC, f.film_id"""

# Q3: os 10 atores com mais filmes
n = func.count().label("films")
q3 = (
    select(Actor.actor_id, Actor.first_name, Actor.last_name, n)
    .join(film_actor, film_actor.c.actor_id == Actor.actor_id)
    .group_by(Actor.actor_id)
    .order_by(n.desc(), Actor.actor_id)
    .limit(10)
)
q3_sql = """SELECT a.actor_id, a.first_name, a.last_name, count(*) AS films
FROM actor a JOIN film_actor fa ON fa.actor_id = a.actor_id
GROUP BY a.actor_id
ORDER BY films DESC, a.actor_id
LIMIT 10"""

with Session(engine) as session:
    for name, orm, handwritten in (("Q1", q1, q1_sql), ("Q2", q2, q2_sql), ("Q3", q3, q3_sql)):
        print(f"\n########## {name} com o ORM")
        orm_rows = [tuple(r) for r in session.execute(orm)]
        print(f"########## {name} com o SQL escrito à mão")
        sql_rows = [tuple(r) for r in session.execute(text(handwritten))]
        print(f"########## {name}: ORM {len(orm_rows)} linhas, SQL {len(sql_rows)} linhas, "
              f"mesmas linhas: {'sim' if orm_rows == sql_rows else 'NÃO'}")
