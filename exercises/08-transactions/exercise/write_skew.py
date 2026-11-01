"""Write skew: regra "cada loja tem pelo menos 1 funcionário ativo".
20 pedidos ao mesmo tempo, cada um desativa um funcionário diferente da loja 1
depois de verificar que há mais de 1 ativo.

    uv run python write_skew.py ex08 read_committed
    uv run python write_skew.py ex08 serializable
"""

import sys
import threading
import time

from psycopg import errors

from db import connect

MODE = sys.argv[2] if len(sys.argv) > 2 else "read_committed"
ISOLATION = {"read_committed": "READ COMMITTED", "serializable": "SERIALIZABLE"}[MODE]

with connect(autocommit=True) as c:
    c.execute("UPDATE staff SET active = true WHERE store_id = 1")
    staff_ids = [r[0] for r in c.execute("SELECT staff_id FROM staff WHERE store_id = 1 ORDER BY 1")]
print(f"{ISOLATION}: {len(staff_ids)} funcionários ativos na loja 1")

barrier = threading.Barrier(len(staff_ids))  # todos começam ao mesmo tempo
results = {"deactivated": 0, "refused": 0, "retries": 0}
lock = threading.Lock()


def deactivate(staff_id):
    barrier.wait()
    while True:
        try:
            with connect() as conn:
                conn.execute(f"SET TRANSACTION ISOLATION LEVEL {ISOLATION}")
                active = conn.execute(
                    "SELECT count(*) FROM staff WHERE store_id = 1 AND active"
                ).fetchone()[0]
                if active <= 1:
                    with lock:
                        results["refused"] += 1
                    return
                time.sleep(0.05)  # a "lógica da aplicação" entre ler e escrever
                conn.execute("UPDATE staff SET active = false WHERE staff_id = %s", (staff_id,))
            with lock:
                results["deactivated"] += 1
            return
        except errors.SerializationFailure:
            # SERIALIZABLE: o PostgreSQL cancelou esta transação; tenta outra vez
            with lock:
                results["retries"] += 1


threads = [threading.Thread(target=deactivate, args=(s,)) for s in staff_ids]
for t in threads:
    t.start()
for t in threads:
    t.join()

with connect() as c:
    active = c.execute("SELECT count(*) FROM staff WHERE store_id = 1 AND active").fetchone()[0]
print(f"desativados={results['deactivated']} recusados={results['refused']} retries={results['retries']}")
print(f"ativos no fim: {active}  ->  {'regra cumprida' if active >= 1 else 'REGRA QUEBRADA'}")
