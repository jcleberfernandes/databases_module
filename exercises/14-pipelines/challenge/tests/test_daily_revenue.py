"""Teste do relatório incremental, em pagila_docs.

    uv run pytest -v -s

No fim apaga os 5 alugueres de teste e o relatório, para rentals ficar como estava.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from bson.decimal128 import Decimal128
from pymongo import MongoClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import MONGO_URL  # noqa: E402
from daily_revenue import day_totals, run_report  # noqa: E402


@pytest.fixture
def db():
    db = MongoClient(MONGO_URL)["pagila_docs"]
    db.drop_collection("daily_revenue")
    db.drop_collection("report_state")
    top = db.rentals.find_one(sort=[("_id", -1)])["_id"]
    yield db
    db.rentals.delete_many({"_id": {"$gt": top}})  # tira os alugueres de teste
    db.drop_collection("daily_revenue")
    db.drop_collection("report_state")


def snapshot(db):
    return {d["_id"]: d for d in db.daily_revenue.find()}


def new_rental(rental_id, when, amount):
    return {"_id": rental_id, "customer_id": 1, "film_id": 1, "title": "ACADEMY DINOSAUR",
            "categories": ["Games", "New", "Travel"], "store_id": 1, "rental_date": when,
            "return_date": None, "amount": Decimal128(amount)}


def test_incremental_report(db):
    # 1. relatório sobre a coleção inteira
    first = run_report(db)
    before = snapshot(db)
    print(f"\n1.ª execução: {len(first)} dias recalculados, daily_revenue com {len(before)} dias")
    assert len(first) == len(before)
    assert "2026-07-28" in before and "2026-07-29" not in before

    # 2. 5 alugueres novos: 3 num dia que já existe e 2 num dia novo
    top = db.rentals.find_one(sort=[("_id", -1)])["_id"]
    utc = timezone.utc
    db.rentals.insert_many([
        new_rental(top + 1, datetime(2026, 7, 28, 10, 0, tzinfo=utc), "2.99"),
        new_rental(top + 2, datetime(2026, 7, 28, 11, 0, tzinfo=utc), "4.99"),
        new_rental(top + 3, datetime(2026, 7, 28, 12, 0, tzinfo=utc), "0.99"),
        new_rental(top + 4, datetime(2026, 7, 29, 9, 0, tzinfo=utc), "1.99"),
        new_rental(top + 5, datetime(2026, 7, 29, 10, 0, tzinfo=utc), "3.99"),
    ])

    # 3. segunda execução: só esses 2 dias mudam
    second = run_report(db)
    after = snapshot(db)
    changed = sorted(day for day in after if after[day] != before.get(day))
    print(f"2.ª execução: recalculou {second}; dias diferentes em daily_revenue: {changed}")
    print(f"   2026-07-28 antes={before['2026-07-28']} depois={after['2026-07-28']}")
    print(f"   2026-07-29 depois={after['2026-07-29']}")
    assert second == ["2026-07-28", "2026-07-29"]
    assert changed == ["2026-07-28", "2026-07-29"]
    assert after["2026-07-28"]["rentals"] == before["2026-07-28"]["rentals"] + 3

    # 4. igual a um recálculo completo, do zero
    full = {d["_id"]: d for d in db.rentals.aggregate(day_totals(db))}
    print(f"4. recálculo completo: {len(full)} dias, igual a daily_revenue: {full == after}")
    assert full == after

    # 5. terceira execução: não muda nada
    third = run_report(db)
    print(f"3.ª execução: recalculou {third}; daily_revenue igual: {snapshot(db) == after}")
    assert third == []
    assert snapshot(db) == after
