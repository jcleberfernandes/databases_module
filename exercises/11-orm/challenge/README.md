# Challenge 11 — Teste automático contra o N+1

Ficheiros:
- `tests/conftest.py` — as fixtures `engine`, `session`, `query_counter` (conta os SQL com o
  evento `before_cursor_execute`) e `assert_max_queries(n)` (context manager).
- `tests/test_queries.py` — o teste.
- `films.py` — o código testado (`list_films`), com os modelos do exercício (`../exercise/models.py`).
- `pyproject.toml`.

```bash
cd exercises/11-orm/challenge
uv run pytest -v
```

## Fixture e helper

```python
@pytest.fixture
def query_counter(engine):
    statements = []
    def count(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)
    event.listen(engine, "before_cursor_execute", count)
    yield statements
    event.remove(engine, "before_cursor_execute", count)

@pytest.fixture
def assert_max_queries(query_counter):
    @contextmanager
    def check(n):
        start = len(query_counter)
        yield
        ran = query_counter[start:]
        assert len(ran) <= n, f"{len(ran)} statements ran (max {n}):\n" + ...
    return check
```

## O teste

```python
def test_list_100_films_with_actors_and_categories(session, assert_max_queries):
    with assert_max_queries(3):
        films = list_films(session)      # selectinload(Film.actors), selectinload(Film.categories)
    assert len(films) == 100
```

## `uv run pytest -v` — com eager loading (passa)

```
tests/test_queries.py::test_list_100_films_with_actors_and_categories PASSED [100%]
============================== 1 passed in 0.20s ===============================
```

Com eager loading são 3 queries: os filmes, os atores dos 100 filmes e as categorias dos 100 filmes.

## `uv run pytest -v` — sem eager loading (falha)

Tirei a linha `.options(selectinload(Film.actors), selectinload(Film.categories))` de `films.py`:

```
tests/test_queries.py::test_list_100_films_with_actors_and_categories FAILED [100%]
E       AssertionError: 201 statements ran (max 3):
E         SELECT film.film_id, film.title, film.length, film.language_id FROM film ORDER BY film.film_id LIMIT %(param_1)s::INTEGE
E         SELECT actor.actor_id, actor.first_name, actor.last_name FROM actor, film_actor WHERE %(param_1)s::INTEGER = film_actor.
E         SELECT category.category_id, category.name FROM category, film_category WHERE %(param_1)s::INTEGER = film_category.film_
E         SELECT actor.actor_id, actor.first_name, actor.last_name FROM actor, film_actor WHERE %(param_1)s::INTEGER = film_actor.
E         SELECT category.category_id, category.name FROM category, film_category WHERE %(param_1)s::INTEGER = film_category.film_
E         SELECT actor.actor_id, actor.first_name, actor.last_name FROM actor, film_actor WHERE %(param_1)s::INTEGER = film_actor.
E         SELECT category.category_id, category.name FROM category, film_category WHERE %(param_1)s::INTEGER = film_category.film_
E         ...
FAILED tests/test_queries.py::test_list_100_films_with_actors_and_categories
============================== 1 failed in 0.41s ===============================
```

A mensagem mostra quantos SQL correram: **201** (1 para os filmes + 100 para os atores + 100 para
as categorias, um por filme). Depois voltei a pôr o eager loading e o teste passa outra vez.
