import os
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

load_dotenv()  # .env deste projeto, se existir (MONGO_URL)
# Sem .env: usa as passwords do .env da raiz do repositório
_root = dotenv_values(Path(__file__).resolve().parents[3] / ".env")
MONGO_URL = os.environ.get("MONGO_URL") or (
    f"mongodb://{_root['MONGO_ROOT_USER']}:{_root['MONGO_ROOT_PASSWORD']}@localhost:27017/?authSource=admin"
)
