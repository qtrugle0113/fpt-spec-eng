"""One target connection owns a native table lock for its entire writer life."""
import hashlib
import time
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from ..contracts.config import identifier
from ..readers.schema import digest

NAMESPACE=718423079


class TargetBusy(ValueError):pass
class SessionLost(ValueError):pass


class TargetSession:
    def __init__(self,engine,*,schema,table,timeout=300):
        self.engine=engine;self.schema=identifier(schema);self.table=identifier(table)
        if isinstance(timeout,bool) or not isinstance(timeout,(int,float)) or not 0<=timeout<=300:
            raise ValueError('Native lock timeout must be between 0 and 300 seconds.')
        self.timeout=timeout;self.connection=None;self.owned=False

    def __enter__(self):
        self.connection=self.engine.connect()
        try:
            c=self.connection;dialect=c.dialect.name
            if dialect=='postgresql':
                self.session_id=c.scalar(text('SELECT pg_backend_pid()'))
                c.execute(text("SET statement_timeout='120s'"))
                endpoint=c.execute(text('SELECT inet_server_addr()::text,inet_server_port(),oid::text FROM pg_database WHERE datname=current_database()')).one()
                server=digest(['POSTGRESQL',*endpoint])
                relation=c.execute(text('SELECT c.oid::bigint,c.relkind FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=:schema AND c.relname=:table'),{'schema':self.schema,'table':self.table}).one()
                if relation[1] not in ('r','p'):raise ValueError('Target must be a base table.')
                self.oid=relation[0];self.signed_oid=self.oid if self.oid<2**31 else self.oid-2**32
                self.physical_identity=digest(['POSTGRESQL',server,self.oid])
            elif dialect=='mysql':
                self.session_id=int(c.scalar(text('SELECT CONNECTION_ID()')))
                server_uuid,lower=c.execute(text('SELECT @@server_uuid,@@lower_case_table_names')).one()
                if lower:self.schema=self.schema.lower();self.table=self.table.lower()
                actual=c.execute(text('SELECT TABLE_SCHEMA,TABLE_NAME,ENGINE,TABLE_TYPE FROM information_schema.TABLES WHERE BINARY TABLE_SCHEMA=BINARY :schema AND BINARY TABLE_NAME=BINARY :table'),{'schema':self.schema,'table':self.table}).one()
                if actual[2]!='InnoDB' or actual[3]!='BASE TABLE':raise ValueError('MySQL target must be an InnoDB base table.')
                server=hashlib.sha256(('MYSQL:'+server_uuid).encode()).hexdigest()
                self.physical_identity=digest(['MYSQL',server,actual[0],actual[1]])
                self.lock_name='aat:'+digest([actual[0],actual[1]])[:60]
                c.execute(text("SET time_zone='+00:00'"))
                mode=c.scalar(text('SELECT @@session.sql_mode'))
                if not {'STRICT_TRANS_TABLES','STRICT_ALL_TABLES'} & set(mode.split(',')):raise ValueError('Strict target SQL mode is required.')
            else:raise ValueError('Unsupported target adapter.')
            deadline=time.monotonic()+self.timeout
            while True:
                acquired=c.scalar(text('SELECT pg_try_advisory_lock(:namespace,:oid)'),{'namespace':NAMESPACE,'oid':self.signed_oid}) if dialect=='postgresql' else c.scalar(text('SELECT GET_LOCK(:name,0)'),{'name':self.lock_name})
                if acquired:self.owned=True;break
                if time.monotonic()>=deadline:raise TargetBusy('Target is busy with another managed run.')
                time.sleep(min(.05,max(0,deadline-time.monotonic())))
            c.commit()
            return self
        except BaseException:
            self.__exit__(None,None,None)
            raise

    def require_owned(self):
        if not self.owned or self.connection is None or self.connection.invalidated or self.connection.closed:
            raise SessionLost('Native target session was lost; reconcile before reconnecting.')
        try:
            c=self.connection
            if c.dialect.name=='postgresql':
                valid=c.scalar(text("SELECT EXISTS(SELECT 1 FROM pg_locks WHERE locktype='advisory' AND pid=pg_backend_pid() AND classid=:namespace AND objid=:oid AND objsubid=2 AND granted)"),{'namespace':NAMESPACE,'oid':self.oid})
                same=c.scalar(text('SELECT pg_backend_pid()'))==self.session_id
            else:
                valid=c.scalar(text('SELECT IS_USED_LOCK(:name)'),{'name':self.lock_name})==self.session_id
                same=c.scalar(text('SELECT CONNECTION_ID()'))==self.session_id
            if not valid or not same:raise SessionLost('Native lock ownership cannot be verified.')
        except SQLAlchemyError:
            self.owned=False;c.invalidate()
            raise SessionLost('Native target session was lost; reconcile before reconnecting.') from None

    def __exit__(self,*error):
        c=self.connection
        if c is None:return
        try:
            if not c.closed and not c.invalidated:
                c.rollback()
                if self.owned:
                    if c.dialect.name=='postgresql':c.execute(text('SELECT pg_advisory_unlock(:namespace,:oid)'),{'namespace':NAMESPACE,'oid':self.signed_oid})
                    else:c.execute(text('SELECT RELEASE_LOCK(:name)'),{'name':self.lock_name})
                    c.commit()
        except SQLAlchemyError:c.invalidate()
        finally:
            self.owned=False;c.close()
