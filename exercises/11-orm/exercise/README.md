# Exercício 11 — ORM (SQLAlchemy 2.0)

Ficheiros: `models.py`, `queries.py`, `n_plus_one.py`, `pyproject.toml`.

```bash
./scripts/create-db.sh ex11 --pagila --reset
cd exercises/11-orm/exercise
uv run python queries.py        # tarefa 2 (echo=True: mostra o SQL que o ORM gera)
uv run python n_plus_one.py     # tarefa 3
```

A ligação vem de `DATABASE_URL`; sem `.env`, o `models.py` usa a password do `.env` da raiz.

## 1. Modelos (`models.py`)

As 6 tabelas, com `Mapped` e `mapped_column`:

| Tabela | Mapeamento | Relações |
|---|---|---|
| `film` | `Film` | `language` (N:1), `actors` (N:N), `categories` (N:N) |
| `language` | `Language` | `films` (1:N) |
| `actor` | `Actor` | `films` (N:N) |
| `category` | `Category` | `films` (N:N) |
| `film_actor` | `Table` de ligação | `secondary` de `Film.actors` / `Actor.films` |
| `film_category` | `Table` de ligação | `secondary` de `Film.categories` / `Category.films` |

## 2. As 3 queries: SQL escrito à mão e SQL gerado

Os três dão as mesmas linhas:

```
########## Q1: ORM 16 linhas, SQL 16 linhas, mesmas linhas: sim
########## Q2: ORM 489 linhas, SQL 489 linhas, mesmas linhas: sim
########## Q3: ORM 10 linhas, SQL 10 linhas, mesmas linhas: sim
```

### Q1 — filmes por categoria

| SQL escrito à mão | SQL gerado pelo ORM (log do `echo=True`) |
|---|---|
| `SELECT c.name, count(*) AS films`<br>`FROM category c JOIN film_category fc ON fc.category_id = c.category_id`<br>`GROUP BY c.category_id, c.name`<br>`ORDER BY films DESC, c.name;` | `SELECT category.name, count(*) AS films`<br>`FROM category JOIN film_category ON film_category.category_id = category.category_id`<br>`GROUP BY category.category_id, category.name`<br>`ORDER BY films DESC, category.name` |

Diferença: o ORM não usa aliases (`c`, `fc`); escreve o nome completo das tabelas. De resto é igual.

### Q2 — filmes mais longos do que a média

| SQL escrito à mão | SQL gerado pelo ORM |
|---|---|
| `SELECT f.film_id, f.title, f.length`<br>`FROM film f`<br>`WHERE f.length > (SELECT avg(length) FROM film)`<br>`ORDER BY f.length DESC, f.film_id;` | `SELECT film.film_id, film.title, film.length`<br>`FROM film`<br>`WHERE film.length > (SELECT avg(film.length) AS avg_1 FROM film)`<br>`ORDER BY film.length DESC, film.film_id` |

Diferença: a subquery (`.scalar_subquery()`) ganha um alias automático (`avg_1`) e qualifica a
coluna (`film.length`). O resultado é o mesmo.

### Q3 — os 10 atores com mais filmes

| SQL escrito à mão | SQL gerado pelo ORM |
|---|---|
| `SELECT a.actor_id, a.first_name, a.last_name, count(*) AS films`<br>`FROM actor a JOIN film_actor fa ON fa.actor_id = a.actor_id`<br>`GROUP BY a.actor_id`<br>`ORDER BY films DESC, a.actor_id`<br>`LIMIT 10;` | `SELECT actor.actor_id, actor.first_name, actor.last_name, count(*) AS films`<br>`FROM actor JOIN film_actor ON film_actor.actor_id = actor.actor_id`<br>`GROUP BY actor.actor_id`<br>`ORDER BY films DESC, actor.actor_id`<br>`LIMIT %(param_1)s::INTEGER` |

Diferença: o `LIMIT 10` é enviado como **parâmetro** (`%(param_1)s`, com o valor 10 à parte), não
escrito no SQL. O ORM faz isso com todos os valores, o que também protege contra SQL injection.

## 3. N+1 — os primeiros 100 filmes e os seus atores

Antes — lazy loading: cada `film.actors` faz uma query nova.

```python
for film in session.scalars(select(Film).order_by(Film.film_id).limit(100)):
    names = ", ".join(f"{a.first_name} {a.last_name}" for a in film.actors)
```

Depois — `selectinload`, numa sessão nova (para nada vir já carregado da anterior):

```python
stmt = select(Film).order_by(Film.film_id).limit(100).options(selectinload(Film.actors))
```

Os `SELECT` contados com o evento `before_cursor_execute`:

```
ANTES (lazy loading):
   último: BROOKLYN DESERT: JODIE DEGENERES, JAYNE NEESON, SEAN GUINESS, ALBERT NOLTE, GROUCHO WILLIAMS
   101 SELECT para 100 filmes
DEPOIS (selectinload):
   último: BROOKLYN DESERT: JODIE DEGENERES, JAYNE NEESON, SEAN GUINESS, ALBERT NOLTE, GROUCHO WILLIAMS
   2 SELECT para 100 filmes
   SELECT film.film_id, film.title, film.length, film.language_id FROM film ORDER BY film.film_id LIMIT %(param_1)s::INTEGER
   SELECT film_actor.film_id, actor.actor_id, actor.first_name, actor.last_name FROM film_actor JOIN actor ON actor.actor_id = film_actor.actor_id WHERE ...
```

**Antes: 101 queries** (1 para os filmes + 1 por filme). **Depois: 2** (os filmes, e todos os atores
desses 100 filmes de uma vez, com `WHERE film_actor.film_id IN (...)`). O resultado é o mesmo.
