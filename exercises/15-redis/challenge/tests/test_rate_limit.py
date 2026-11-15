import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rate_limit import allow_request_fixed, allow_request_sliding, r  # noqa: E402

CUSTOMER = 999_001
MINUTE = 1_800_000_000  # um instante que é início de minuto (divisível por 60)


@pytest.fixture(autouse=True)
def clean():
    for key in r.scan_iter(f"ratelimit:*:{CUSTOMER}*"):
        r.delete(key)
    yield
    for key in r.scan_iter(f"ratelimit:*:{CUSTOMER}*"):
        r.delete(key)


def burst():
    """10 pedidos aos segundos 59.0 a 59.9 de um minuto e 10 aos 0.0 a 0.9 do seguinte."""
    end_of_minute = [MINUTE + 59 + i / 10 for i in range(10)]
    next_minute = [MINUTE + 60 + i / 10 for i in range(10)]
    return end_of_minute + next_minute


def test_fixed_window_accepts_20_but_sliding_only_10():
    fixed = [allow_request_fixed(CUSTOMER, t) for t in burst()]
    sliding = [allow_request_sliding(CUSTOMER, t) for t in burst()]
    print(f"\njanela fixa:      {sum(fixed)} aceites de 20  {fixed}")
    print(f"janela deslizante: {sum(sliding)} aceites de 20  {sliding}")
    assert sum(fixed) == 20      # 10 no minuto M e 10 no minuto M+1: 20 pedidos em ~2 s
    assert sum(sliding) == 10    # em qualquer janela de 60 s só cabem 10
    assert sliding == [True] * 10 + [False] * 10


def test_sliding_window_under_concurrency():
    now = MINUTE + 30.0
    barrier = threading.Barrier(10)
    accepted = []
    lock = threading.Lock()

    def client():
        barrier.wait()                       # as 10 threads arrancam ao mesmo tempo
        for _ in range(3):                   # 3 pedidos cada = 30 pedidos, todos com a mesma hora
            ok = allow_request_sliding(CUSTOMER, now)
            with lock:
                accepted.append(ok)

    threads = [threading.Thread(target=client) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f"\n30 pedidos de 10 threads: {sum(accepted)} aceites, {accepted.count(False)} recusados")
    assert len(accepted) == 30
    assert sum(accepted) == 10
    assert r.zcard(f"ratelimit:sliding:{CUSTOMER}") == 10   # membros únicos mesmo com a mesma hora
