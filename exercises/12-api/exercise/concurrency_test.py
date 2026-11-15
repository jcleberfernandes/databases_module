"""5 POST /rentals ao mesmo tempo para o filme 7 na loja 1 (clientes 1 a 5, staff 6).
O filme 7 tem só 2 cópias na loja 1: esperado 2 x 201 e 3 x 409, com 2 inventory_id diferentes.

Com a API a correr (uv run uvicorn app.main:app) numa cópia nova do Pagila com as migrações:
    uv run python concurrency_test.py
"""

import threading

import httpx

URL = "http://127.0.0.1:8000/rentals"
barrier = threading.Barrier(5)  # os 5 pedidos saem ao mesmo tempo
results = {}


def rent(customer_id):
    with httpx.Client() as client:
        barrier.wait()
        r = client.post(URL, json={"customer_id": customer_id, "film_id": 7, "store_id": 1, "staff_id": 6})
        results[customer_id] = (r.status_code, r.json())


threads = [threading.Thread(target=rent, args=(c,)) for c in range(1, 6)]
for t in threads:
    t.start()
for t in threads:
    t.join()

for customer_id in sorted(results):
    print(f"cliente {customer_id}: {results[customer_id][0]} {results[customer_id][1]}")

created = [body for status, body in results.values() if status == 201]
conflicts = [body for status, body in results.values() if status == 409]
copies = {body["inventory_id"] for body in created}
print(f"201: {len(created)}  409: {len(conflicts)}  inventory_id diferentes: {sorted(copies)}")
ok = len(created) == 2 and len(conflicts) == 3 and len(copies) == 2
print("OK" if ok else "FALHOU")
raise SystemExit(0 if ok else 1)
