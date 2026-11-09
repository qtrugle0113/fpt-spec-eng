"""Application metadata migrations only; initialized with an explicit connection."""
from alembic import context

connection=context.config.attributes.get('connection')
if connection is None:raise RuntimeError('Run migrations through owner app-init with its migration lock')
context.configure(connection=connection,transactional_ddl=True)
with context.begin_transaction():context.run_migrations()
