"""Lê o Pagila (PostgreSQL) e escreve as coleções films, customers e rentals (MongoDB).

    uv run python load.py

Pode correr várias vezes: o _id de cada documento é o id do Pagila e cada documento é
escrito com replace_one(upsert=True), por isso a 2.ª execução deixa os mesmos documentos.
"""

import time

import psycopg
from bson.decimal128 import Decimal128
from psycopg.rows import dict_row
from pymongo import MongoClient, ReplaceOne

from config import DATABASE_URL, MONGO_DB, MONGO_URL

FILMS = """
SELECT f.film_id AS _id, f.title, f.release_year::int AS release_year, l.name AS language,
       f.rating::text AS rating, f.length::int AS length, f.rental_duration::int AS rental_duration,
       f.rental_rate,
       coalesce((SELECT array_agg(c.name ORDER BY c.name)
                 FROM film_category fc JOIN category c USING (category_id)
                 WHERE fc.film_id = f.film_id), '{}') AS categories,
       coalesce((SELECT json_agg(json_build_object('actor_id', a.actor_id,
                                                   'name', a.first_name || ' ' || a.last_name)
                                 ORDER BY a.actor_id)
                 FROM film_actor fa JOIN actor a USING (actor_id)
                 WHERE fa.film_id = f.film_id), '[]') AS actors
FROM film f
JOIN language l USING (language_id)
ORDER BY f.film_id
"""

CUSTOMERS = """
SELECT c.customer_id AS _id, c.first_name, c.last_name, c.email, c.store_id,
       ci.city, co.country,
       (SELECT count(*) FROM rental r WHERE r.customer_id = c.customer_id)::int AS rental_count
FROM customer c
JOIN address a  USING (address_id)
JOIN city ci    USING (city_id)
JOIN country co USING (country_id)
ORDER BY c.customer_id
"""

# Os 10 alugueres mais recentes de cada cliente
RECENT = """
SELECT customer_id, rental_id, film_id, title, rental_date, return_date
FROM (
    SELECT r.customer_id, r.rental_id, i.film_id, f.title, r.rental_date, r.return_date,
           row_number() OVER (PARTITION BY r.customer_id
                              ORDER BY r.rental_date DESC, r.rental_id DESC) AS pos
    FROM rental r
    JOIN inventory i USING (inventory_id)
    JOIN film f      USING (film_id)
) x
WHERE pos <= 10
ORDER BY customer_id, pos
"""

RENTALS = """
WITH film_categories AS (
    SELECT fc.film_id, array_agg(c.name ORDER BY c.name) AS categories
    FROM film_category fc JOIN category c USING (category_id)
    GROUP BY fc.film_id
),
rental_amount AS (
    -- uma só passagem por payment (sem subquery por aluguer)
    SELECT rental_id, sum(amount) AS amount FROM payment GROUP BY rental_id
)
SELECT r.rental_id AS _id, r.customer_id, i.film_id, f.title,
       coalesce(fc.categories, '{}') AS categories,
       i.store_id, r.rental_date, r.return_date,
       coalesce(ra.amount, 0) AS amount
FROM rental r
JOIN inventory i USING (inventory_id)
JOIN film f      USING (film_id)
LEFT JOIN film_categories fc ON fc.film_id = i.film_id
LEFT JOIN rental_amount ra   ON ra.rental_id = r.rental_id
ORDER BY r.rental_id
"""


def write(collection, docs):
    started = time.perf_counter()
    result = collection.bulk_write([ReplaceOne({"_id": d["_id"]}, d, upsert=True) for d in docs])
    print(f"{collection.name:<10} {len(docs):>6} documentos  "
          f"(novos={result.upserted_count}, alterados={result.modified_count}) "
          f"em {time.perf_counter() - started:.1f} s")


with psycopg.connect(DATABASE_URL, row_factory=dict_row) as pg, MongoClient(MONGO_URL) as mongo:
    db = mongo[MONGO_DB]

    films = pg.execute(FILMS).fetchall()
    for f in films:
        f["rental_rate"] = Decimal128(f["rental_rate"])  # dinheiro em Decimal128, nunca float
    write(db.films, films)

    recent = {}
    for r in pg.execute(RECENT):
        recent.setdefault(r.pop("customer_id"), []).append(r)
    customers = []
    for c in pg.execute(CUSTOMERS):
        customers.append({
            "_id": c["_id"], "first_name": c["first_name"], "last_name": c["last_name"],
            "email": c["email"], "store_id": c["store_id"],
            "address": {"city": c["city"], "country": c["country"]},
            "rental_count": c["rental_count"],
            "recent_rentals": recent.get(c["_id"], []),
        })
    write(db.customers, customers)

    rentals = pg.execute(RENTALS).fetchall()
    for r in rentals:
        r["amount"] = Decimal128(r["amount"])
    write(db.rentals, rentals)
