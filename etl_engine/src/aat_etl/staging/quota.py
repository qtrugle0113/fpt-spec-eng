"""Atomic app-metadata capacity reservations, never heartbeat-based reclamation."""
from contextlib import contextmanager
from pathlib import Path
import shutil
from uuid import UUID,uuid4
from sqlalchemy import text

RUN_LIMIT=10*1024**3
GLOBAL_LIMIT=20*1024**3
MIN_FREE=1024**3
LOCK=718423076


class QuotaExceeded(ValueError):pass


class QuotaManager:
    def __init__(self,engine,root):
        if engine.dialect.name!='postgresql' or engine.url.database!='app_metadata':raise ValueError('Quota accounting requires the application metadata database.')
        self.engine=engine;self.root=Path(root)
        if self.root.is_symlink() or not self.root.is_dir():raise ValueError('An existing staging root is required.')

    @contextmanager
    def atomic(self):
        with self.engine.connect().execution_options(isolation_level='READ COMMITTED') as connection:
            with connection.begin():
                connection.execute(text('SELECT pg_advisory_xact_lock(:lock)'),{'lock':LOCK})
                yield connection

    def totals(self,connection,run):
        row=connection.execute(text("""SELECT COALESCE(sum(reserved_bytes) FILTER (WHERE run_uuid=:run),0),
          COALESCE(sum(reserved_bytes),0),COALESCE(sum(reserved_bytes-written_bytes),0)
          FROM staging_reservations WHERE state<>'RELEASED'"""),{'run':run}).one()
        return dict(run_reserved_bytes=int(row[0]),global_reserved_bytes=int(row[1]),unwritten_reserved_bytes=int(row[2]))

    def usage(self,run):
        with self.atomic() as connection:return self.totals(connection,UUID(str(run)))

    def reserve(self,run,attempt,size):
        if type(size) is not int or size<1:raise ValueError('A positive integer reservation size is required.')
        run=UUID(str(run));attempt=UUID(str(attempt))
        with self.atomic() as connection:
            existing=connection.execute(text('SELECT id,requested_bytes,state FROM staging_reservations WHERE run_uuid=:run AND attempt_id=:attempt'),{'run':run,'attempt':attempt}).first()
            if existing:
                if existing[1]!=size or existing[2]=='RELEASED':raise ValueError('Reservation identity cannot be reused for another allocation.')
                return existing[0]
            current=self.totals(connection,run)
            if current['run_reserved_bytes']+size>RUN_LIMIT:raise QuotaExceeded('Run staging quota exceeds 10 GiB.')
            if current['global_reserved_bytes']+size>GLOBAL_LIMIT:raise QuotaExceeded('Global staging quota exceeds 20 GiB, including protected and incomplete artifacts.')
            if shutil.disk_usage(self.root).free-current['unwritten_reserved_bytes']-size<MIN_FREE:raise QuotaExceeded('Staging capacity would violate the 1 GiB free-disk reserve.')
            identity=uuid4()
            connection.execute(text('INSERT INTO staging_reservations (id,run_uuid,attempt_id,requested_bytes,reserved_bytes) VALUES (:id,:run,:attempt,:bytes,:bytes)'),
                {'id':identity,'run':run,'attempt':attempt,'bytes':size})
            return identity

    def require(self,connection,identity):
        value=connection.execute(text('SELECT * FROM staging_reservations WHERE id=:id FOR UPDATE'),{'id':identity}).mappings().first()
        if value is None:raise ValueError('Staging reservation does not exist.')
        return value

    def seal(self,identity,written_bytes):
        if type(written_bytes) is not int or written_bytes<0:raise ValueError('Written bytes must be a nonnegative integer.')
        with self.atomic() as connection:
            value=self.require(connection,identity)
            if value['state']=='PROTECTED' and value['written_bytes']==written_bytes:return
            if value['state']!='ACTIVE' or written_bytes>value['reserved_bytes']:raise ValueError('Cannot seal this staging reservation.')
            connection.execute(text("UPDATE staging_reservations SET reserved_bytes=:bytes,written_bytes=:bytes,state='PROTECTED',updated_at=now() WHERE id=:id"),{'id':identity,'bytes':written_bytes})

    def protect(self,identity):
        with self.atomic() as connection:
            value=self.require(connection,identity)
            if value['state']=='RELEASED':raise ValueError('Released capacity cannot be adopted by another writer.')
            if value['state']=='ACTIVE':connection.execute(text("UPDATE staging_reservations SET state='PROTECTED',updated_at=now() WHERE id=:id"),{'id':identity})

    def release_after_cleanup(self,identity,*,writer_stopped,artifacts_removed,reconciled):
        if writer_stopped is not True or artifacts_removed is not True or reconciled is not True:
            raise ValueError('Release requires confirmed writer termination, artifact removal and completed reconciliation.')
        with self.atomic() as connection:
            value=self.require(connection,identity)
            if value['state']=='RELEASED':return
            connection.execute(text("UPDATE staging_reservations SET state='RELEASED',writer_stopped_at=now(),artifacts_removed_at=now(),reconciled_at=now(),updated_at=now() WHERE id=:id"),{'id':identity})
