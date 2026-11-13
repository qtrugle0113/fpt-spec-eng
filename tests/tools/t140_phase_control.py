"""Read T140 runtime state or hold a row lock in an owned PostgreSQL target."""
import json
import re
import sys

from sqlalchemy import text

from aat_api.services.connections.service import transaction
from aat_api.services.table_preview import target_engine


TABLE = re.compile(r"full_(?:desktop|mobile)_[0-9]+")


def target_revision(code):
    with transaction() as session:
        revision = session.scalar(
            text("SELECT current_revision_id FROM connections WHERE normalized_code=:code"),
            {"code": code},
        )
    if revision is None:
        raise ValueError("Owned target connection was not found.")
    return revision


def owned_table(value):
    if not TABLE.fullmatch(value):
        raise ValueError("Target table is outside the T140 fixture namespace.")
    return value


def hold_target(value):
    table = owned_table(value["table"])
    row_id = int(value["lock_row_id"])
    revision = target_revision(value["code"])
    with target_engine(revision) as engine:
        if engine.dialect.name != "postgresql":
            raise ValueError("T140 phase lock requires the owned PostgreSQL fixture.")
        name = engine.dialect.identifier_preparer.quote_identifier(table)
        with engine.begin() as connection:
            connection.execute(
                text(
                    f"INSERT INTO public.{name} "
                    "(customer_id,customer_name,balance,registered_at) "
                    "VALUES (:id,'old protected row',0,NULL) ON CONFLICT (customer_id) DO NOTHING"
                ),
                {"id": row_id},
            )
        with engine.connect() as connection:
            lock_transaction = connection.begin()
            try:
                row = connection.execute(
                    text(f"SELECT customer_id FROM public.{name} WHERE customer_id=:id FOR UPDATE"),
                    {"id": row_id},
                ).first()
                if row is None:
                    raise RuntimeError("Owned lock row was not created.")
                print("LOCK_HELD", flush=True)
                sys.stdin.readline()
            finally:
                lock_transaction.rollback()


def runtime_state(dag, run, code, table):
    table = owned_table(table)
    with transaction() as session:
        row = session.execute(
            text(
                """
                SELECT b.id AS binding_id,b.state AS binding_state,b.commit_uncertain,
                    r.config_json->>'retry_count' AS retry_count,
                    b.dataset_id,d.state AS dataset_state,d.extracted_rows,d.validated_rows,
                    d.path_key,d.manifest_sha256,l.owner_process_id,l.recovery_state,
                    m.loaded_rows,m.phase,
                    (SELECT count(*) FROM staging_artifacts a
                     WHERE a.dataset_id=b.dataset_id) AS staging_artifacts,
                    (SELECT count(*) FROM staging_artifacts a
                     WHERE a.dataset_id=b.dataset_id AND a.recovery_protected) AS protected_artifacts,
                    (SELECT json_agg(json_build_object('id',r.id,'state',r.state,
                                                       'reserved_bytes',r.reserved_bytes)
                                     ORDER BY r.created_at)
                     FROM staging_reservations r
                     JOIN run_intents i ON i.run_uuid=r.run_uuid
                     WHERE i.id=b.run_intent_id) AS reservations,
                    (SELECT json_agg(json_build_object('id',d.id,'generation',d.generation,
                                                       'state',d.state,'manifest_sha256',d.manifest_sha256)
                                     ORDER BY d.generation)
                     FROM dataset_manifests d
                     WHERE d.execution_binding_id=b.id) AS dataset_generations
                FROM execution_bindings b
                JOIN etl_definition_revisions r ON r.id=b.etl_revision_id
                LEFT JOIN dataset_manifests d ON d.id=b.dataset_id
                LEFT JOIN runtime_leases l ON l.binding_id=b.id
                LEFT JOIN execution_metrics m ON m.binding_id=b.id
                WHERE b.dag_id=:dag AND b.airflow_run_id=:run
                """
            ),
            {"dag": dag, "run": run},
        ).mappings().one_or_none()
    if row is None:
        return None

    activity = []
    revision = target_revision(code)
    with target_engine(revision) as engine, engine.connect() as connection:
        if engine.dialect.name == "postgresql":
            activity = connection.execute(
                text(
                    """
                    SELECT CASE
                        WHEN query ILIKE '%DELETE FROM%' THEN 'FULL_REFRESH_DELETE'
                        WHEN query ILIKE '%INSERT INTO%' THEN 'UPSERT_INSERT'
                        ELSE 'OTHER'
                    END AS operation
                    FROM pg_stat_activity
                    WHERE wait_event_type='Lock' AND query ILIKE :needle
                    """
                ),
                {"needle": "%" + table + "%"},
            ).scalars().all()
    return {**dict(row), "blocked_operations": activity}


def airflow_task(dag, run):
    from aat_api.services.runtime_binding import airflow

    task = airflow().task(dag, run, "execute_etl")
    keys = ("state", "try_number", "max_tries", "hostname", "pid", "start_date", "end_date")
    return {key: task.get(key) for key in keys}


def airflow_task_logs(dag, run, attempt):
    from aat_api.services.monitoring import log_page

    return log_page(dag, run, "execute_etl", attempt=int(attempt), map_index=-1)


def target_rows(code, table):
    table = owned_table(table)
    revision = target_revision(code)
    with target_engine(revision) as engine, engine.connect() as connection:
        name = engine.dialect.identifier_preparer.quote_identifier(table)
        rows = connection.execute(
            text(
                f"SELECT customer_id,customer_name,balance,registered_at "
                f"FROM public.{name} ORDER BY customer_id"
            )
        ).all()
    return [
        [
            row.customer_id,
            row.customer_name,
            str(row.balance) if row.balance is not None else None,
            row.registered_at.isoformat() if row.registered_at is not None else None,
        ]
        for row in rows
    ]


def main():
    command = sys.argv[1]
    if command == "hold":
        hold_target(json.loads(sys.stdin.readline()))
        return
    if command == "state":
        print(json.dumps(runtime_state(*sys.argv[2:]), default=str), flush=True)
        return
    if command == "task":
        print(json.dumps(airflow_task(*sys.argv[2:]), default=str), flush=True)
        return
    if command == "logs":
        print(json.dumps(airflow_task_logs(*sys.argv[2:]), default=str), flush=True)
        return
    if command == "target":
        print(json.dumps(target_rows(*sys.argv[2:])), flush=True)
        return
    raise ValueError("Unsupported T140 phase-control command.")


if __name__ == "__main__":
    main()
