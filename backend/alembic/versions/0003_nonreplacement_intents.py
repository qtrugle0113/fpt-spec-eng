"""APPEND/UPSERT run identity does not grant replacement authority."""
from alembic import op

revision='0003_nonreplacement_intents'
down_revision='0002_staging_quota'
branch_labels=None
depends_on=None


def upgrade():
    op.alter_column('run_intents','authorization_id',nullable=True)


def downgrade():
    raise RuntimeError('Automatic metadata downgrade is unsupported; restore a verified backup')
