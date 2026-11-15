"""Relatório daily_revenue (um documento por dia) mantido de forma incremental com $merge.

    uv run python daily_revenue.py        # corre o relatório em pagila_docs

Cada execução:
1. lê o watermark em report_state (o maior rentals._id já processado);
2. encontra os dias dos alugueres com _id acima do watermark;
3. recalcula esses dias inteiros, a partir de TODOS os alugueres desses dias;
4. junta-os a daily_revenue com $merge (whenMatched: "replace");
5. só depois avança o watermark.
"""

from pymongo import MongoClient

from config import MONGO_URL

STATE_ID = "daily_revenue"
DAY = {"$dateToString": {"date": "$rental_date", "format": "%Y-%m-%d"}}


def day_totals(db, days=None):
    """Pipeline que agrupa os alugueres por dia. days=None: todos os dias."""
    pipeline = [{"$set": {"day": DAY}}]
    if days is not None:
        pipeline.append({"$match": {"day": {"$in": days}}})
    pipeline.append({"$group": {"_id": "$day", "rentals": {"$sum": 1}, "revenue": {"$sum": "$amount"}}})
    return pipeline


def run_report(db) -> list[str]:
    """Atualiza daily_revenue e devolve os dias recalculados."""
    state = db.report_state.find_one({"_id": STATE_ID}) or {"watermark": -1}
    watermark = state["watermark"]

    newest = db.rentals.find_one({"_id": {"$gt": watermark}}, sort=[("_id", -1)])
    if newest is None:
        return []  # nada de novo: não toca em nada
    new_max = newest["_id"]

    new_days = sorted(d["_id"] for d in db.rentals.aggregate([
        {"$match": {"_id": {"$gt": watermark, "$lte": new_max}}},
        {"$group": {"_id": DAY}},
    ]))

    db.rentals.aggregate(day_totals(db, new_days) + [
        {"$merge": {"into": "daily_revenue", "on": "_id", "whenMatched": "replace", "whenNotMatched": "insert"}},
    ])
    # o watermark só avança depois do $merge: se o processo morrer antes, a próxima
    # execução volta a recalcular os mesmos dias (e o resultado é o mesmo)
    db.report_state.update_one({"_id": STATE_ID}, {"$set": {"watermark": new_max}}, upsert=True)
    return new_days


if __name__ == "__main__":
    db = MongoClient(MONGO_URL)["pagila_docs"]
    days = run_report(db)
    print(f"dias recalculados: {len(days)}" + (f" ({days[0]} ... {days[-1]})" if days else ""))
    print(f"daily_revenue: {db.daily_revenue.count_documents({})} dias")
