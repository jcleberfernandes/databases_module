"""contract: apagar customer.email (só depois de parar a v1)

Revision ID: 0005
Revises: 0004
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# A mesma função da 0004 (o downgrade volta a deixar a base como depois do expand)
SYNC_FUNCTION = """
CREATE FUNCTION customer_sync_email() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        NEW.email_address := coalesce(NEW.email_address, NEW.email);
        NEW.email := coalesce(NEW.email, NEW.email_address);
    ELSIF NEW.email IS DISTINCT FROM OLD.email THEN
        NEW.email_address := NEW.email;
    ELSIF NEW.email_address IS DISTINCT FROM OLD.email_address THEN
        NEW.email := NEW.email_address;
    END IF;
    RETURN NEW;
END $$;
"""


def upgrade() -> None:
    op.execute("DROP TRIGGER customer_sync_email ON customer")
    op.execute("DROP FUNCTION customer_sync_email()")
    op.drop_column("customer", "email")


def downgrade() -> None:
    op.add_column("customer", sa.Column("email", sa.Text(), nullable=True))
    op.execute("UPDATE customer SET email = email_address")
    op.execute(SYNC_FUNCTION)
    op.execute("""
        CREATE TRIGGER customer_sync_email BEFORE INSERT OR UPDATE ON customer
        FOR EACH ROW EXECUTE FUNCTION customer_sync_email()
    """)
