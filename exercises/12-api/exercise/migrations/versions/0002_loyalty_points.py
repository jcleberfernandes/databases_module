"""customer.loyalty_points em três passos

Revision ID: 0002
Revises: 0001

Um add_column(..., nullable=False) direto falhava (a tabela já tem linhas).
Por isso: 1) adicionar como nullable, 2) preencher com o nº de alugueres,
3) pôr NOT NULL. O server_default 0 serve para clientes novos.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("customer", sa.Column("loyalty_points", sa.Integer(), nullable=True))
    op.execute("""
        UPDATE customer c
        SET loyalty_points = (SELECT count(*) FROM rental r WHERE r.customer_id = c.customer_id)
    """)
    op.alter_column("customer", "loyalty_points", nullable=False, server_default=sa.text("0"))


def downgrade() -> None:
    op.drop_column("customer", "loyalty_points")
