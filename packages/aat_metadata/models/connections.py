"""Connection metadata and immutable credential revisions; no public CRUD API.

PostgreSQL DDL listeners enforce direct-SQL immutability too. T029 must carry
these guards into actual Alembic migrations; importing models never touches DB.
Only explicit whitelist projections are public. Never serialize ORM __dict__.
"""

import base64
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint, Computed, DateTime, DDL, ForeignKey, ForeignKeyConstraint,
    Integer, String, Text, UniqueConstraint, event, func, select,
)
from sqlalchemy.orm import Mapped, mapped_column, validates

from .base import Base


class ConnectionSecret(Base):
    __tablename__ = 'connection_secrets'
    __table_args__ = (
        CheckConstraint("key_id ~ '^[0-9a-f]{32}$'", name='ck_connection_secret_key_id'),
        CheckConstraint("ciphertext ~ '^gA[A-Za-z0-9_-]+={0,2}$' AND length(ciphertext)>=100", name='ck_connection_secret_token'),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    ciphertext: Mapped[str] = mapped_column(Text)
    key_id: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @validates('ciphertext')
    def validate_token(self, key, value):
        try:
            raw = base64.b64decode(value, altchars=b'-_', validate=True)
            valid = len(raw) >= 73 and raw[0] == 128 and (len(raw) - 57) % 16 == 0
        except (ValueError, TypeError):
            valid = False
        if not valid:
            raise ValueError('Expected an encrypted Fernet token')
        return value

    @classmethod
    def from_plaintext(cls, codec, plaintext: str):
        key_id, ciphertext = codec.encrypt(plaintext)
        return cls(key_id=key_id, ciphertext=ciphertext)


class Connection(Base):
    __tablename__ = 'connections'
    __table_args__ = (
        UniqueConstraint('normalized_code', name='uq_connections_normalized_code'),
        CheckConstraint("length(btrim(code))>0", name='ck_connections_code'),
        CheckConstraint("length(btrim(name))>0", name='ck_connections_name'),
        CheckConstraint("database_type IN ('POSTGRESQL','MYSQL')", name='ck_connections_database_type'),
        ForeignKeyConstraint(['id', 'current_revision_id'],
                             ['connection_revisions.connection_id', 'connection_revisions.id'],
                             name='fk_connections_current_revision', ondelete='RESTRICT', use_alter=True),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(64))
    normalized_code: Mapped[str] = mapped_column(String(64), Computed('lower(btrim(code))', persisted=True))
    name: Mapped[str] = mapped_column(String(255))
    database_type: Mapped[str] = mapped_column(String(16))
    current_revision_id: Mapped[UUID | None]
    description: Mapped[str | None] = mapped_column(Text)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    @validates('code')
    def trim_code(self, key, value):
        return value.strip() if isinstance(value, str) else value

    def public_dict(self):
        return {key: getattr(self, key) for key in ('id', 'code', 'name', 'database_type', 'description')}


class ConnectionRevision(Base):
    __tablename__ = 'connection_revisions'
    __table_args__ = (
        UniqueConstraint('connection_id', 'revision', name='uq_connection_revisions_number'),
        UniqueConstraint('connection_id', 'id', name='uq_connection_revisions_owner_id'),
        CheckConstraint('revision>=1', name='ck_connection_revisions_number'),
        CheckConstraint('port BETWEEN 1 AND 65535', name='ck_connection_revisions_port'),
        CheckConstraint("database_type IN ('POSTGRESQL','MYSQL')", name='ck_connection_revisions_database_type'),
        CheckConstraint("length(btrim(host))>0 AND length(btrim(database_name))>0 AND length(btrim(username))>0", name='ck_connection_revisions_required_endpoint'),
        CheckConstraint("test_status IN ('UNTESTED','SUCCESS','FAILED')", name='ck_connection_revisions_test_status'),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    connection_id: Mapped[UUID] = mapped_column(ForeignKey('connections.id', ondelete='RESTRICT'))
    revision: Mapped[int] = mapped_column(Integer)
    database_type: Mapped[str] = mapped_column(String(16))
    host: Mapped[str] = mapped_column(String(255))
    port: Mapped[int] = mapped_column(Integer)
    database_name: Mapped[str] = mapped_column(String(255))
    schema_name: Mapped[str | None] = mapped_column(String(255))
    username: Mapped[str] = mapped_column(String(255))
    secret_id: Mapped[UUID] = mapped_column(ForeignKey('connection_secrets.id', ondelete='RESTRICT'))
    physical_server_fingerprint: Mapped[str | None] = mapped_column(String(64))
    test_status: Mapped[str] = mapped_column(String(16), default='UNTESTED', server_default='UNTESTED')
    tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def public_dict(self):
        return {key: getattr(self, key) for key in ('id', 'connection_id', 'revision', 'database_type', 'host', 'port',
                                                   'database_name', 'schema_name', 'username', 'test_status', 'tested_at')}


def immutable_guard(table, columns):
    expression = ' OR '.join(f'NEW.{column} IS DISTINCT FROM OLD.{column}' for column in columns)
    ddl = f"""CREATE OR REPLACE FUNCTION public.aat_guard_{table}() RETURNS trigger
    LANGUAGE plpgsql AS $$ BEGIN
      IF {expression} THEN
        RAISE EXCEPTION 'Stored revision or credential is immutable' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER aat_immutable BEFORE UPDATE ON {table}
    FOR EACH ROW EXECUTE FUNCTION public.aat_guard_{table}();"""
    event.listen(Base.metadata.tables[table], 'after_create', DDL(ddl).execute_if(dialect='postgresql'))


@event.listens_for(ConnectionRevision, 'before_insert')
def snapshot_database_type(mapper, connection, revision):
    if revision.database_type is None:
        revision.database_type = connection.scalar(
            select(Connection.database_type).where(Connection.id == revision.connection_id))


immutable_guard('connection_revisions', ('id', 'connection_id', 'revision', 'database_type', 'host', 'port',
                                       'database_name', 'schema_name', 'username', 'secret_id'))
immutable_guard('connection_secrets', ('id', 'ciphertext', 'key_id'))

# Business dependencies in later real model tables block code changes. Owned
# revisions alone do not block an otherwise unreferenced connection rename.
CODE_DEPENDENCY_GUARD = """CREATE OR REPLACE FUNCTION public.aat_guard_connection_code()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE ref record; found boolean;
BEGIN
  IF NEW.code IS NOT DISTINCT FROM OLD.code THEN RETURN NEW; END IF;
  FOR ref IN
    SELECT fk.conrelid::regclass AS relation, child.attname AS column_name,
           fk.confrelid='public.connections'::regclass AS direct
    FROM pg_constraint fk
    JOIN pg_attribute parent ON parent.attrelid=fk.confrelid AND parent.attname='id'
    JOIN pg_attribute child ON child.attrelid=fk.conrelid
      AND child.attnum=fk.conkey[array_position(fk.confkey,parent.attnum)]
    WHERE fk.contype='f' AND parent.attnum=ANY(fk.confkey)
      AND fk.confrelid IN ('public.connections'::regclass,'public.connection_revisions'::regclass)
      AND fk.conrelid NOT IN ('public.connections'::regclass,'public.connection_revisions'::regclass)
  LOOP
    IF ref.direct THEN
      EXECUTE format('SELECT EXISTS(SELECT 1 FROM %s WHERE %I=$1)',ref.relation,ref.column_name) INTO found USING OLD.id;
    ELSE
      EXECUTE format('SELECT EXISTS(SELECT 1 FROM %s WHERE %I IN (SELECT id FROM public.connection_revisions WHERE connection_id=$1))',ref.relation,ref.column_name) INTO found USING OLD.id;
    END IF;
    IF found THEN RAISE EXCEPTION 'Connection code has dependencies' USING ERRCODE='23514'; END IF;
  END LOOP;
  RETURN NEW;
END $$;
CREATE TRIGGER aat_code_dependency BEFORE UPDATE OF code ON public.connections
FOR EACH ROW EXECUTE FUNCTION public.aat_guard_connection_code();"""
event.listen(ConnectionRevision.__table__, 'after_create',
             DDL(CODE_DEPENDENCY_GUARD.replace('%', '%%')).execute_if(dialect='postgresql'))
