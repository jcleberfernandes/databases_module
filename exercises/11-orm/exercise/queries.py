"""Ponto 2: 3 queries do exercício 05 reescritas com o ORM.
Mostra o SQL gerado pelo SQLAlchemy e confirma que o resultado é igual ao do SQL escrito à mão.

    uv run python queries.py
"""

from sqlalchemy import func, select, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session, aliased

from db import engine
from models import Actor, Category, film_actor, film_category

# --- Q6 do exercício 05: número de filmes por categoria
films = func.count().label("films")
q6_orm = (
    select(Category.name, films)
    .join(film_category, film_category.c.category_id == Category.category_id)
    .group_by(Category.name)
    .order_by(films.desc(), Category.name)
)
q6_sql = """
SELECT c.name, count(*) AS films
FROM category c
JOIN film_category fc ON fc.category_id = c.category_id
GROUP BY c.name
ORDER BY films DESC, c.name"""

# --- Q4 do exercício 05: pares de atores com mais de 3 filmes juntos (self join)
fa1, fa2 = aliased(film_actor), aliased(film_actor)
a1, a2 = aliased(Actor), aliased(Actor)
together = func.count().label("films")
q4_orm = (
    select(
        (a1.first_name + " " + a1.last_name).label("actor_1"),
        (a2.first_name + " " + a2.last_name).label("actor_2"),
        together,
    )
    .select_from(fa1)
    .join(fa2, (fa2.c.film_id == fa1.c.film_id) & (fa2.c.actor_id > fa1.c.actor_id))
    .join(a1, a1.actor_id == fa1.c.actor_id)
    .join(a2, a2.actor_id == fa2.c.actor_id)
    .group_by(a1.actor_id, a2.actor_id)
    .having(func.count() > 3)
    .order_by(together.desc(), "actor_1", "actor_2")
)
q4_sql = """
SELECT a1.first_name || ' ' || a1.last_name AS actor_1,
       a2.first_name || ' ' || a2.last_name AS actor_2,
       count(*) AS films
FROM film_actor fa1
JOIN film_actor fa2 ON fa2.film_id = fa1.film_id AND fa2.actor_id > fa1.actor_id
JOIN actor a1 ON a1.actor_id = fa1.actor_id
JOIN actor a2 ON a2.actor_id = fa2.actor_id
GROUP BY a1.actor_id, a2.actor_id
HAVING count(*) > 3
ORDER BY films DESC, actor_1, actor_2"""

# --- Q9 do exercício 05: atores que nunca entraram num filme de Horror (subquery)
horror_actors = (
    select(film_actor.c.actor_id)
    .join(film_category, film_category.c.film_id == film_actor.c.film_id)
    .join(Category, Category.category_id == film_category.c.category_id)
    .where(Category.name == "Horror")
)
q9_orm = (
    select(Actor.actor_id, Actor.first_name, Actor.last_name)
    .where(Actor.actor_id.not_in(horror_actors))
    .order_by(Actor.actor_id)
)
q9_sql = """
SELECT a.actor_id, a.first_name, a.last_name
FROM actor a
WHERE a.actor_id NOT IN (
    SELECT fa.actor_id
    FROM film_actor fa
    JOIN film_category fc ON fc.film_id = fa.film_id
    JOIN category c       ON c.category_id = fc.category_id
    WHERE c.name = 'Horror'
)
ORDER BY a.actor_id"""

with Session(engine) as session:
    for name, orm, handwritten in [
        ("Q6 filmes por categoria", q6_orm, q6_sql),
        ("Q4 pares de atores", q4_orm, q4_sql),
        ("Q9 atores sem Horror", q9_orm, q9_sql),
    ]:
        generated = orm.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
        orm_rows = [tuple(r) for r in session.execute(orm)]
        sql_rows = [tuple(r) for r in session.execute(text(handwritten))]
        print(f"===== {name}")
        print("--- SQL gerado pelo ORM:")
        print(generated)
        print(f"--- linhas ORM={len(orm_rows)}  linhas SQL à mão={len(sql_rows)}  "
              f"iguais={'sim' if orm_rows == sql_rows else 'NÃO'}\n")
