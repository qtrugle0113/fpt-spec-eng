"""Permit required intent row locks through one reconciliation timestamp column."""
from alembic import op

revision='0004_runtime_intent_lock'
down_revision='0003_nonreplacement_intents'
branch_labels=None
depends_on=None


def upgrade():
    op.execute('GRANT UPDATE(last_reconciled_at) ON public.run_intents TO aat_etl')


def downgrade():
    raise RuntimeError('Automatic metadata downgrade is unsupported; restore a verified backup')
