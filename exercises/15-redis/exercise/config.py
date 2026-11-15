import os
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

load_dotenv()  # .env deste projeto, se existir
# Sem .env: usa as passwords do .env da raiz do repositório
_root = dotenv_values(Path(__file__).resolve().parents[3] / ".env")

DATABASE_URL = os.environ.get("DATABASE_URL") or (
    f"postgresql://{_root['POSTGRES_USER']}:{_root['POSTGRES_PASSWORD']}@localhost:5432/ex15"
)
REDIS_URL = os.environ.get("REDIS_URL") or f"redis://:{_root['REDIS_PASSWORD']}@localhost:6379/0"
