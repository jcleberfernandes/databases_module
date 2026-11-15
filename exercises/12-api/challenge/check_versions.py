"""Muda o email numa versão da API e lê-o na outra, nos dois sentidos.

Com as duas versões a correr (portas 8001 e 8002):
    uv run python check_versions.py
Só a v2 (depois do contract):
    uv run python check_versions.py --only-v2
"""

import sys

import httpx

V1, V2 = "http://127.0.0.1:8001", "http://127.0.0.1:8002"
CUSTOMER = 1
ok = True


def change_and_read(write_url, read_url, email):
    global ok
    w = httpx.put(f"{write_url}/customers/{CUSTOMER}/email", json={"email": email})
    r = httpx.get(f"{read_url}/customers/{CUSTOMER}")
    seen = r.json().get("email")
    same = w.status_code == 200 and seen == email
    ok &= same
    print(f"PUT {write_url} email={email} -> {w.status_code} | GET {read_url} -> {r.status_code} email={seen} "
          f"{'OK' if same else 'DIFERENTE'}")


if "--only-v2" in sys.argv:
    change_and_read(V2, V2, "mary.v2.only@example.com")
    try:
        httpx.get(f"{V1}/customers/{CUSTOMER}", timeout=1)
        print("v1 ainda está a responder")
    except httpx.ConnectError:
        print("v1 parada (como deve estar depois do contract)")
else:
    change_and_read(V1, V2, "mary.from.v1@example.com")
    change_and_read(V2, V1, "mary.from.v2@example.com")

print("OK" if ok else "FALHOU")
raise SystemExit(0 if ok else 1)
