"""no máximo um aluguer aberto por cópia

Revision ID: 0003
Revises: 0002

Três cópias (1358, 1435 e 2408) têm dois alugueres abertos cada. Antes de criar
o índice único parcial é preciso corrigir os dados: o aluguer aberto mais antigo
de cada cópia fica fechado com a rental_date do mais recente.
O downgrade só apaga o índice; a correção dos dados não se desfaz (ver README).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Data migration: fecha os alugueres abertos a mais (todos menos o mais recente de cada cópia)
    op.execute("""
        WITH open_rental AS (
            SELECT rental_id,
                   row_number() OVER w AS pos,
                   first_value(rental_date) OVER w AS newest_rental_date
            FROM rental
            WHERE return_date IS NULL
            WINDOW w AS (PARTITION BY inventory_id ORDER BY rental_date DESC, rental_id DESC)
        )
        UPDATE rental r
        SET return_date = o.newest_rental_date
        FROM open_rental o
        WHERE o.rental_id = r.rental_id AND o.pos > 1
    """)
    op.create_index(
        "rental_one_open_per_copy", "rental", ["inventory_id"],
        unique=True, postgresql_where=sa.text("return_date IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("rental_one_open_per_copy", table_name="rental")
