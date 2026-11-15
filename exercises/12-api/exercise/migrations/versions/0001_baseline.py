"""baseline: o schema do Pagila tal como já existe

Revision ID: 0001
Revises:

O Pagila foi criado pelos seus próprios scripts SQL, antes do Alembic.
Esta revisão marca esse ponto de partida: não faz nada.
Numa base que já tem o schema corre-se `alembic stamp head` (ou `stamp 0001`).
"""
from typing import Sequence, Union

revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
