"""Explicit metadata privileges; runtime cannot grant scope or delete evidence."""
from sqlalchemy import text


def apply_grants(connection):
    # Roles already belong to DB bootstrap; app-init never invents credentials.
    for role in ['aat_app_runtime','aat_etl']:
        if not connection.scalar(text('SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=:role)'),{'role':role}):
            raise RuntimeError('Required application role missing')
    connection.execute(text('REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC'))
    connection.execute(text('REVOKE CREATE ON SCHEMA public FROM PUBLIC'))
    connection.execute(text('GRANT CONNECT ON DATABASE app_metadata TO aat_etl'))
    connection.execute(text('GRANT USAGE ON SCHEMA public TO aat_app_runtime,aat_etl'))
    connection.execute(text('GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO aat_app_runtime'))
    connection.execute(text('REVOKE DELETE ON audit_events,replacement_authorizations,run_intents,replacement_admissions,execution_bindings,dataset_manifests,staging_artifacts,staging_reservations FROM aat_app_runtime'))
    connection.execute(text('GRANT SELECT ON ALL TABLES IN SCHEMA public TO aat_etl'))
    connection.execute(text('GRANT INSERT ON execution_bindings,dataset_manifests,staging_artifacts,execution_metrics,runtime_leases,replacement_admissions TO aat_etl'))
    # PostgreSQL row-lock reads require UPDATE on at least one column. The
    # reconciliation timestamp permits the intent lock without state/scope writes.
    connection.execute(text('GRANT UPDATE(last_reconciled_at) ON run_intents TO aat_etl'))
    connection.execute(text('GRANT UPDATE(state,commit_uncertain,dataset_id,last_reconciled_at,updated_at) ON execution_bindings TO aat_etl'))
    connection.execute(text('GRANT UPDATE(state,reconciled_at,writer_finished,updated_at) ON replacement_admissions TO aat_etl'))
    connection.execute(text('GRANT UPDATE(state,revision,consumed_at,closed_at,updated_at) ON replacement_authorizations TO aat_etl'))
    connection.execute(text('GRANT UPDATE(state,manifest_sha256,extracted_rows,validated_rows,total_bytes,updated_at) ON dataset_manifests TO aat_etl'))
    connection.execute(text('GRANT UPDATE ON execution_metrics,runtime_leases TO aat_etl'))
    connection.execute(text('GRANT INSERT ON staging_reservations TO aat_etl'))
    connection.execute(text('GRANT UPDATE(reserved_bytes,written_bytes,state,writer_stopped_at,artifacts_removed_at,reconciled_at,updated_at) ON staging_reservations TO aat_etl'))
