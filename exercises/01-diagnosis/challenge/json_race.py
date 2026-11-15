"""10 processos acrescentam 1 000 registos cada ao mesmo ficheiro JSON, sem lock:
ler o ficheiro inteiro, juntar um registo, escrever o ficheiro inteiro.

    uv run python json_race.py
"""

import json
from multiprocessing import Pool
from pathlib import Path

FILE = Path(__file__).with_name("records.json")
WORKERS = 10
RECORDS = 1_000


def append_records(worker: int) -> int:
    failed = 0
    for n in range(RECORDS):
        try:
            data = json.loads(FILE.read_text())
            data.append({"worker": worker, "n": n})
            FILE.write_text(json.dumps(data))
        except json.JSONDecodeError:
            # leu o ficheiro a meio de ser escrito por outro processo
            failed += 1
    return failed


if __name__ == "__main__":
    FILE.write_text("[]")
    with Pool(WORKERS) as pool:
        failed = sum(pool.map(append_records, range(WORKERS)))
    text = FILE.read_text()
    try:
        count, valid = len(json.loads(text)), "válido"
    except json.JSONDecodeError:
        # Duas escritas sobrepuseram-se e ficou lixo no fim do ficheiro:
        # conta os registos da lista válida que está no início
        records, end = json.JSONDecoder().raw_decode(text)
        count, valid = len(records), f"INVÁLIDO (lixo depois do carácter {end})"
    print(f"JSON: {count} registos no ficheiro (esperado {WORKERS * RECORDS}), "
          f"{failed} escritas falhadas, ficheiro {valid}")
