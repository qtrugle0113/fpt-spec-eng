"""Allow one confirmed workbook operation to retain per-DAG deployment results."""
from alembic import op

revision='0005_deployment_operation_dags'
down_revision='0004_runtime_intent_lock'
branch_labels=None
depends_on=None


def upgrade():
    op.drop_constraint('dag_deployments_operation_id_key','dag_deployments',type_='unique')
    op.create_unique_constraint('uq_deployment_operation_dag','dag_deployments',['operation_id','dag_id'])


def downgrade():
    raise RuntimeError('Automatic metadata downgrade is unsupported; restore a verified backup')
