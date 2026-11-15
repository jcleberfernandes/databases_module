"""Challenge 13: padrão bucket para o histórico de alugueres.

    uv run python buckets.py

1. cria rental_buckets (no máximo 50 alugueres por documento) com add_rental(), por ordem de rental_date
2. cria rental_history (um documento por cliente com todos os alugueres)
3. compara as duas para o cliente 380: tamanho dos documentos e tempo para ler os 20 mais recentes
"""

import sys
import time
from pathlib import Path

import bson
from pymongo import ASCENDING, MongoClient
from pymongo.errors import DuplicateKeyError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "exercise"))
from config import MONGO_DB, MONGO_URL  # noqa: E402  (reutiliza a configuração do exercício)

BUCKET_SIZE = 50

db = MongoClient(MONGO_URL)[MONGO_DB]
buckets = db.rental_buckets


def add_rental(customer_id: int, rental: dict) -> None:
    """Junta o aluguer ao bucket aberto do cliente, ou abre um bucket novo."""
    while True:
        # seq do bucket a abrir, caso o atual esteja cheio (= nº de buckets que o cliente já tem)
        next_seq = buckets.count_documents({"customer_id": customer_id})
        try:
            buckets.update_one(
                # o filtro em count: só serve um bucket com espaço
                {"customer_id": customer_id, "count": {"$lt": BUCKET_SIZE}},
                {
                    "$push": {"rentals": rental},
                    "$inc": {"count": 1},
                    # só quando não há bucket com espaço e o upsert cria um novo
                    "$setOnInsert": {"seq": next_seq},
                },
                upsert=True,
            )
            return
        except DuplicateKeyError:
            # Outra chamada abriu o bucket com este seq ao mesmo tempo: tenta outra vez
            # (agora o filtro já encontra esse bucket novo, que tem espaço).
            continue


def load_buckets() -> None:
    db.drop_collection("rental_buckets")
    # Garante que nunca há dois buckets com o mesmo seq para o mesmo cliente
    buckets.create_index([("customer_id", ASCENDING), ("seq", ASCENDING)], unique=True)
    started = time.perf_counter()
    cursor = db.rentals.find({}, {"categories": 0, "store_id": 0}).sort([("rental_date", 1), ("_id", 1)])
    n = 0
    for r in cursor:
        add_rental(r.pop("customer_id"), {"rental_id": r.pop("_id"), **r})
        n += 1
    print(f"rental_buckets: {n} alugueres em {buckets.count_documents({})} buckets "
          f"({time.perf_counter() - started:.1f} s)")


def load_history() -> None:
    # Um documento por cliente com TODOS os alugueres, por ordem de rental_date
    db.rentals.aggregate([
        {"$sort": {"rental_date": 1, "_id": 1}},
        {"$group": {
            "_id": "$customer_id",
            "count": {"$sum": 1},
            "rentals": {"$push": {"rental_id": "$_id", "film_id": "$film_id", "title": "$title",
                                  "rental_date": "$rental_date", "return_date": "$return_date",
                                  "amount": "$amount"}},
        }},
        {"$out": "rental_history"},
    ], allowDiskUse=True)
    print(f"rental_history: {db.rental_history.count_documents({})} documentos")


def check() -> None:
    biggest = buckets.find_one(sort=[("count", -1)])["count"]
    print(f"maior bucket: {biggest} alugueres (máximo {BUCKET_SIZE})")
    for b in buckets.find({"customer_id": 380}, {"seq": 1, "count": 1, "_id": 0}).sort("seq", 1):
        print(f"cliente 380: {b}")


def compare(customer_id: int = 380, runs: int = 1000) -> None:
    for b in buckets.find({"customer_id": customer_id}).sort("seq", 1):
        print(f"rental_buckets seq={b['seq']} count={b['count']} tamanho={len(bson.encode(b))} bytes")
    h = db.rental_history.find_one({"_id": customer_id})
    print(f"rental_history count={h['count']} tamanho={len(bson.encode(h))} bytes")

    # Os alugueres estão por ordem de rental_date: os 20 mais recentes são os últimos 20
    def from_buckets():
        last = buckets.find_one({"customer_id": customer_id}, {"rentals": {"$slice": -20}, "count": 1},
                                sort=[("seq", -1)])
        rentals = last["rentals"]
        if last["count"] < 20:  # o último bucket tem poucos: completa com o anterior
            prev = buckets.find_one({"customer_id": customer_id, "seq": {"$lt": last["seq"]}},
                                    {"rentals": {"$slice": last["count"] - 20}}, sort=[("seq", -1)])
            rentals = prev["rentals"] + rentals
        return rentals

    def from_history():
        return db.rental_history.find_one({"_id": customer_id}, {"rentals": {"$slice": -20}})["rentals"]

    for name, read in (("rental_buckets", from_buckets), ("rental_history", from_history)):
        started = time.perf_counter()
        for _ in range(runs):
            rentals = read()
        ms = (time.perf_counter() - started) * 1000 / runs
        print(f"{name}: {len(rentals)} alugueres, o mais recente {rentals[-1]['rental_id']} | "
              f"{ms:.3f} ms por leitura (média de {runs})")


if __name__ == "__main__":
    load_buckets()
    load_history()
    check()
    compare()
