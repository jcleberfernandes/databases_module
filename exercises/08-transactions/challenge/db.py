import os
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

load_dotenv()
_root = dotenv_values(Path(__file__).resolve().parents[3] / ".env")
DATABASE_URL = os.environ.get("DATABASE_URL") or (
    f"postgresql://{_root['POSTGRES_USER']}:{_root['POSTGRES_PASSWORD']}@localhost:5432/ch08"
)
