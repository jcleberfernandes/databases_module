"""expand: customer.email_address ao lado de customer.email

Revision ID: 0004
Revises: 0003

1. adicionar email_address
2. copiar os valores de email (backfill)
3. trigger que mantém as duas colunas iguais enquanto as duas versões da API correm
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SYNC_FUNCTION = """
CREATE FUNCTION customer_sync_email() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        NEW.email_address := coalesce(NEW.email_address, NEW.email);
        NEW.email := coalesce(NEW.email, NEW.email_address);
    ELSIF NEW.email IS DISTINCT FROM OLD.email THEN
        NEW.email_address := NEW.email;          -- a v1 mudou email
    ELSIF NEW.email_address IS DISTINCT FROM OLD.email_address THEN
        NEW.email := NEW.email_address;          -- a v2 mudou email_address
    END IF;
    RETURN NEW;
END $$;
"""


def upgrade() -> None:
    op.add_column("customer", sa.Column("email_address", sa.Text(), nullable=True))
    op.execute("UPDATE customer SET email_address = email")
    op.execute(SYNC_FUNCTION)
    # BEFORE: altera a própria linha antes de ser gravada, sem UPDATE extra (logo sem recursão)
    op.execute("""
        CREATE TRIGGER customer_sync_email BEFORE INSERT OR UPDATE ON customer
        FOR EACH ROW EXECUTE FUNCTION customer_sync_email()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER customer_sync_email ON customer")
    op.execute("DROP FUNCTION customer_sync_email()")
    op.drop_column("customer", "email_address")
