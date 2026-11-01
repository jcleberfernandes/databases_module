"""Compare concurrent writes to a JSON file and PostgreSQL."""

from __future__ import annotations

import argparse
import json
import os
from multiprocessing import Pool
from pathlib import Path
from typing import Any

import psycopg


WORKERS = 10
RECORDS_PER_WORKER = 1_000
DEFAULT_JSON_FILE = Path(__file__).with_name("messages.json")


def load_environment() -> None:
    """Load the repository .env when DATABASE_URL is not already set."""
    if os.getenv("DATABASE_URL"):
        return

    env_file = Path(__file__).resolve().parents[3] / ".env"
    if not env_file.exists():
        return

    for line in env_file.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key, value)


def database_url() -> str:
    load_environment()
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]

    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "change-me-postgres")
    return f"postgresql://{user}:{password}@localhost:5432/s01_fastapi"


def append_to_json(args: tuple[str, int, int]) -> int:
    """Read, append and write without a lock, intentionally exposing the race."""
    filename, worker_id, records = args
    errors = 0

    for record_number in range(records):
        try:
            with open(filename, "r", encoding="utf-8") as file:
                data: list[dict[str, Any]] = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            data = []

        data.append({"worker": worker_id, "record": record_number})

        try:
            with open(filename, "w", encoding="utf-8") as file:
                json.dump(data, file)
        except OSError:
            errors += 1

    return errors


def run_json(filename: Path) -> tuple[int, int]:
    filename.write_text("[]", encoding="utf-8")
    jobs = [(str(filename), worker_id, RECORDS_PER_WORKER) for worker_id in range(WORKERS)]

    with Pool(WORKERS) as pool:
        errors = sum(pool.map(append_to_json, jobs))

    try:
        with filename.open(encoding="utf-8") as file:
            count = len(json.load(file))
    except (OSError, json.JSONDecodeError):
        count = 0

    return count, errors


def insert_into_postgres(args: tuple[int, int]) -> int:
    worker_id, records = args
    with psycopg.connect(database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO challenge_messages (worker_id, record_number) VALUES (%s, %s)",
                [(worker_id, record_number) for record_number in range(records)],
            )
    return records


def run_postgres() -> int:
    with psycopg.connect(database_url()) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS challenge_messages (
                id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                worker_id integer NOT NULL,
                record_number integer NOT NULL
            )
            """
        )
        connection.execute("TRUNCATE challenge_messages")

    jobs = [(worker_id, RECORDS_PER_WORKER) for worker_id in range(WORKERS)]
    with Pool(WORKERS) as pool:
        sum(pool.map(insert_into_postgres, jobs))

    with psycopg.connect(database_url()) as connection:
        return connection.execute("SELECT count(*) FROM challenge_messages").fetchone()[0]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-file", type=Path, default=DEFAULT_JSON_FILE)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    expected = WORKERS * RECORDS_PER_WORKER
    json_count, json_errors = run_json(args.json_file)
    postgres_count = run_postgres()

    print(f"Esperado: {expected} registros")
    print(f"JSON: {json_count} registros (erros de escrita: {json_errors})")
    print(f"PostgreSQL: {postgres_count} registros")
    print(
        "Diferença: cada processo JSON lê uma versão antiga e depois grava a sua "
        "versão. Assim, uma gravação pode substituir a de outro processo. "
        "O PostgreSQL recebe as gravações por conexões separadas e organiza "
        "cada INSERT, por isso mantém os registros concorrentes."
    )


if __name__ == "__main__":
    main()
