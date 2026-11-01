# Challenge 11 — Testes que contam queries

Ficheiros:
- `conftest.py` — fixtures `session`, `query_counter` (evento `before_cursor_execute`) e `assert_max_queries(n)` (context manager).
- `test_films.py` — os testes.
- Reutiliza `db.py` e `models.py` de `../exercise/`.

```bash
cd exercises/11-orm/challenge
uv run pytest -v
uv run pytest --runxfail test_films.py::test_n_plus_one_is_caught   # ver o teste a falhar
```

## Fixture e helper

```python
@pytest.fixture
def query_counter():
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
        made = query_counter[start:]
        assert len(made) <= n, f"{len(made)} queries (máximo {n}) ..."
    return check
```

## Testes

```python
def test_list_100_films_with_actors_and_categories(session, assert_max_queries):
    with assert_max_queries(3):
        films = list_films(session)            # selectinload(actors) + selectinload(categories)

@pytest.mark.xfail(strict=True, reason="N+1 de propósito: o teste TEM de falhar")
def test_n_plus_one_is_caught(session, assert_max_queries):
    with assert_max_queries(3):
        list_films(session, eager=False)       # sem selectinload -> N+1
```

`strict=True`: se o N+1 deixasse de ser apanhado, o teste passava e o pytest marcava-o como erro.

## Resultado

```
test_films.py::test_list_100_films_with_actors_and_categories PASSED     [ 33%]
test_films.py::test_counter_counts_queries PASSED                        [ 66%]
test_films.py::test_n_plus_one_is_caught XFAIL (N+1 de propósito: o ...) [100%]
========================= 2 passed, 1 xfailed in 0.60s =========================
```

Com o N+1 introduzido, o teste apanha-o (`--runxfail`):

```
E       AssertionError: 201 queries (máximo 3):
E         SELECT film.film_id, film.title, film.length, film.rating, film.language_id FROM film ORDER BY film.film_id LIMIT ...
E         SELECT actor.actor_id, actor.first_name, actor.last_name FROM actor, film_actor WHERE %(param_1)s::INTEGER = film_actor. ...
E         SELECT category.category_id, category.name FROM category, film_category WHERE %(param_1)s::INTEGER = film_category.film_ ...
...
```

1 query para os filmes + 100 para os atores + 100 para as categorias = **201**; com `selectinload` são **3**.
