# As migrações do challenge continuam a cadeia do exercício (0001 a 0003), por isso o
# alembic.ini aponta version_locations para as duas pastas. São escritas à mão: sem autogenerate.
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from db import DATABASE_URL

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

connectable = create_engine(DATABASE_URL, poolclass=pool.NullPool)
with connectable.connect() as connection:
    context.configure(connection=connection, target_metadata=None)
    with context.begin_transaction():
        context.run_migrations()
