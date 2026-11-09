"""Durable staging reservations; preserve the frozen initial migration."""
from alembic import op

revision='0002_staging_quota'
down_revision='0001_metadata'
branch_labels=None
depends_on=None


def upgrade():
    op.execute("""CREATE TABLE staging_reservations (
      id uuid PRIMARY KEY,
      run_uuid uuid NOT NULL,
      attempt_id uuid NOT NULL,
      requested_bytes bigint NOT NULL CHECK (requested_bytes>0),
      reserved_bytes bigint NOT NULL CHECK (reserved_bytes>=0),
      written_bytes bigint NOT NULL DEFAULT 0 CHECK (written_bytes>=0 AND written_bytes<=reserved_bytes),
      state varchar(16) NOT NULL DEFAULT 'ACTIVE' CHECK (state IN ('ACTIVE','PROTECTED','RELEASED')),
      writer_stopped_at timestamptz,
      artifacts_removed_at timestamptz,
      reconciled_at timestamptz,
      created_at timestamptz NOT NULL DEFAULT now(),
      updated_at timestamptz NOT NULL DEFAULT now(),
      UNIQUE(run_uuid,attempt_id),
      CHECK (state<>'RELEASED' OR (writer_stopped_at IS NOT NULL AND artifacts_removed_at IS NOT NULL AND reconciled_at IS NOT NULL))
    )""")
    op.execute('CREATE INDEX ix_staging_reservations_run_state ON staging_reservations(run_uuid,state)')
    op.execute("""CREATE FUNCTION public.aat_staging_reservation_guard() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
      IF ROW(NEW.id,NEW.run_uuid,NEW.attempt_id,NEW.requested_bytes,NEW.created_at)
        IS DISTINCT FROM ROW(OLD.id,OLD.run_uuid,OLD.attempt_id,OLD.requested_bytes,OLD.created_at)
        OR OLD.state='RELEASED' AND NEW IS DISTINCT FROM OLD
        OR OLD.state='PROTECTED' AND (NEW.state='ACTIVE' OR NEW.reserved_bytes<>OLD.reserved_bytes OR NEW.written_bytes<>OLD.written_bytes)
      THEN RAISE EXCEPTION 'Staging reservation identity or protected accounting is immutable' USING ERRCODE='23514'; END IF;
      RETURN NEW; END $$""")
    op.execute('CREATE TRIGGER aat_staging_reservation_guard BEFORE UPDATE ON staging_reservations FOR EACH ROW EXECUTE FUNCTION public.aat_staging_reservation_guard()')


def downgrade():raise RuntimeError('Automatic metadata downgrade is unsupported; restore a verified backup')
