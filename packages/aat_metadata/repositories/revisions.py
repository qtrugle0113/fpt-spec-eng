"""Optimistic metadata updates; HTTP mapping belongs to API boundary."""
from psycopg.types.json import Jsonb


class StaleRevision(ValueError):
    pass


def update_setting(connection,key,expected_revision,value):
    row=connection.execute('UPDATE application_settings SET value_json=%s WHERE key=%s AND revision=%s RETURNING revision',
                           (Jsonb(value),key,expected_revision)).fetchone()
    if row is None:raise StaleRevision('Metadata revision changed')
    return row[0]


def update_versioned(session,model,identity,expected_revision,changes,allowed_fields):
    from sqlalchemy import update
    if not changes or set(changes)-set(allowed_fields):raise ValueError('Unsupported metadata fields')
    statement=update(model).where(model.id==identity,model.revision==expected_revision).values(**changes).returning(model.revision)
    revision=session.scalar(statement.execution_options(synchronize_session=False))
    if revision is None:raise StaleRevision('Metadata revision changed')
    return revision
