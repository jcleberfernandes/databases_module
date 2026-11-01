# Exercício 11 — ORM (SQLAlchemy)

Ficheiros:
- `models.py` — 6 tabelas do Pagila com as relações.
- `queries.py` — 3 queries do exercício 05 com o ORM, SQL gerado e comparação.
- `n_plus_one.py` — N+1 de propósito, contagem, correção e nova contagem.
- `db.py` — engine e contador de queries (evento `before_cursor_execute`); lê `POSTGRES_USER`/`POSTGRES_PASSWORD` do `.env` da raiz.

```bash
./scripts/create-db.sh ex11 --pagila
cd exercises/11-orm/exercise
uv run python queries.py
uv run python n_plus_one.py
```

## 1. Mapeamento de 6 tabelas

| Tabela | Classe | Relações |
|---|---|---|
| `film` | `Film` | `language` (N:1), `actors` (N:N), `categories` (N:N) |
| `language` | `Language` | `films` (1:N) |
| `actor` | `Actor` | `films` (N:N) |
| `category` | `Category` | `films` (N:N) |
| `film_actor` | `Table` de ligação | liga `film` ↔ `actor` |
| `film_category` | `Table` de ligação | liga `film` ↔ `category` |

As tabelas de ligação só têm as duas chaves, por isso são `Table` e usadas em `relationship(secondary=...)`.

## 2. Três queries do exercício 05 com o ORM

**Q6 — filmes por categoria**

SQL à mão:
```sql
SELECT c.name, count(*) AS films
FROM category c JOIN film_category fc ON fc.category_id = c.category_id
GROUP BY c.name ORDER BY films DESC, c.name
```
SQL gerado:
```sql
SELECT category.name, count(*) AS films
FROM category JOIN film_category ON film_category.category_id = category.category_id
GROUP BY category.name ORDER BY films DESC, category.name
```
Igual; o ORM usa o nome completo das tabelas em vez de aliases. 16 linhas nos dois.

**Q4 — pares de atores com mais de 3 filmes juntos (self join)**

SQL gerado:
```sql
SELECT actor_1.first_name || ' ' || actor_1.last_name AS actor_1,
       actor_2.first_name || ' ' || actor_2.last_name AS actor_2, count(*) AS films
FROM film_actor AS film_actor_1
JOIN film_actor AS film_actor_2 ON film_actor_2.film_id = film_actor_1.film_id
                               AND film_actor_2.actor_id > film_actor_1.actor_id
JOIN actor AS actor_1 ON actor_1.actor_id = film_actor_1.actor_id
JOIN actor AS actor_2 ON actor_2.actor_id = film_actor_2.actor_id
GROUP BY actor_1.actor_id, actor_2.actor_id
HAVING count(*) > 3 ORDER BY films DESC, actor_1, actor_2
```
Mesma estrutura que o SQL à mão; `aliased()` gera os aliases `film_actor_1`, `actor_1`, ... 143 linhas nos dois.

**Q9 — atores que nunca entraram num filme de Horror (subquery)**

SQL gerado:
```sql
SELECT actor.actor_id, actor.first_name, actor.last_name
FROM actor
WHERE (actor.actor_id NOT IN (SELECT film_actor.actor_id
    FROM film_actor JOIN film_category ON film_category.film_id = film_actor.film_id
    JOIN category ON category.category_id = film_category.category_id
    WHERE category.name = 'Horror')) ORDER BY actor.actor_id
```
Igual ao SQL à mão (só parênteses a mais). 4 linhas nos dois.

Saída do `queries.py`:
```
--- linhas ORM=16  linhas SQL à mão=16  iguais=sim
--- linhas ORM=143  linhas SQL à mão=143  iguais=sim
--- linhas ORM=4  linhas SQL à mão=4  iguais=sim
```

## 3. N+1 (filmes e os seus atores)

Antes — lazy loading, cada `film.actors` faz uma query:
```python
films = session.scalars(select(Film).order_by(Film.film_id).limit(50)).all()
for f in films:
    names = ", ".join(a.last_name for a in f.actors)
```
Depois — `selectinload` carrega os atores de todos os filmes de uma vez:
```python
stmt = select(Film).options(selectinload(Film.actors)).order_by(Film.film_id).limit(50)
```

```
ANTES  (lazy):        51 queries para 50 filmes
  1.ª: SELECT film.film_id, film.title, film.length, film.rating, film.language_id ...
  2.ª: SELECT actor.actor_id, actor.first_name, actor.last_name FROM actor, film_actor
       WHERE %(param_1)s::INTEGER = film_actor.film_id AND actor.actor_id = film_actor.actor_id
DEPOIS (selectinload): 2 queries para 50 filmes
  SELECT film.film_id, film.title, ... FROM film ORDER BY film.film_id LIMIT ...
  SELECT film_actor.film_id, actor.actor_id, ... FROM film_actor JOIN actor ON ... WHERE film_actor.film_id IN (...)
```

**51 → 2 queries.** Com N filmes, o lazy faz 1 + N queries; o `selectinload` faz sempre 2.
