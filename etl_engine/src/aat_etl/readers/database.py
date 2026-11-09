"""One read-only source session per dataset, bounded before transport."""
from datetime import date,datetime,timezone
from decimal import Decimal
import sys
from sqlalchemy import MetaData,Table,case,cast,func,literal,select,Text
from ..contracts.config import SourceFilter,identifier,parse_timestamp

MAX_ROW_BYTES=1024*1024
BUFFER_BYTES=8*1024*1024


class SourceReadError(ValueError):pass


def literal_value(value):
    if value.value is None:return None
    if value.logical_type=='decimal':return Decimal(value.value)
    if value.logical_type=='date':return date.fromisoformat(value.value)
    if value.logical_type=='timestamp':return parse_timestamp(value.value)
    return value.value


class DatabaseSnapshotReader:
    dialect=None

    def __init__(self,engine,*,schema,table,columns,chunk_rows=1000,filter=None):
        self.engine=engine;self.schema=identifier(schema);self.table_name=identifier(table)
        if not columns or len(columns)>1000 or len(set(columns))!=len(columns):raise ValueError('Project 1 to 1000 unique source columns.')
        self.columns=tuple(identifier(v) for v in columns)
        if self.dialect=='postgresql' and any(len(v)>63 for v in (self.schema,self.table_name,*self.columns)):
            raise ValueError('PostgreSQL identifiers cannot exceed 63 bytes.')
        if type(chunk_rows) is not int or not 1<=chunk_rows<=10000:raise ValueError('Extraction chunk rows must be between 1 and 10000.')
        # A single astral character can widen an otherwise ASCII Python string
        # to four bytes per character. Reserve that expansion and object headers.
        self.fetch_rows=min(chunk_rows,max(1,BUFFER_BYTES//(4*MAX_ROW_BYTES+128*len(self.columns))))
        self.filter=SourceFilter.model_validate(filter) if filter is not None else None
        self.connection=None;self.cursor=None;self.consumed=False

    def __enter__(self):
        if self.connection is not None:raise ValueError('Snapshot reader is already open.')
        if self.engine.dialect.name!=self.dialect:raise ValueError('Source engine does not match its adapter.')
        self.connection=self.engine.connect().execution_options(isolation_level='REPEATABLE READ')
        try:
            self.prepare_session()
            self.table=Table(self.table_name,MetaData(),schema=self.schema,autoload_with=self.connection)
            if any(v not in self.table.c for v in self.columns):raise SourceReadError('A projected source column is missing.')
            from .schema import column_profile
            self.profiles=[column_profile(dict(name=name,type=self.table.c[name].type,nullable=self.table.c[name].nullable),self.dialect) for name in self.columns]
            return self
        except BaseException as error:
            self.__exit__(None,None,None)
            if isinstance(error,(ValueError,KeyboardInterrupt,SystemExit)):raise
            raise SourceReadError('Source snapshot could not be opened.') from None

    def prepare_session(self):raise NotImplementedError

    def statement(self):
        projected=[self.table.c[name] for name in self.columns]
        # CASE executes on the server. An oversized projected value never crosses
        # the driver boundary, even when one cell alone is much larger than RAM.
        sizes=[func.coalesce(func.octet_length(cast(c,Text)),0) for c in projected]
        size=sum(sizes,literal(0))
        statement=select(*projected,size.label(None)).select_from(self.table)
        if self.filter:
            for predicate in self.filter.and_:
                if predicate.column not in self.table.c:raise SourceReadError('A source filter column is missing.')
                column=self.table.c[predicate.column];op=predicate.operator
                if op=='IS NULL':condition=column.is_(None)
                elif op=='IS NOT NULL':condition=column.is_not(None)
                elif op=='IN':condition=column.in_([literal_value(v) for v in predicate.value])
                else:
                    value=literal_value(predicate.value)
                    condition={'=':lambda:column==value,'!=':lambda:column!=value,'<':lambda:column<value,
                        '<=':lambda:column<=value,'>':lambda:column>value,'>=':lambda:column>=value}[op]()
                statement=statement.where(condition)
        bounded=statement.subquery()
        measured=list(bounded.c)[-1]
        return select(*[case((measured>MAX_ROW_BYTES,None),else_=bounded.c[name]).label(name) for name in self.columns],measured)

    def rows(self):
        if self.connection is None or self.consumed:raise SourceReadError('Snapshot must be open and consumed only once.')
        self.consumed=True
        try:
            self.connection.exec_driver_sql('SELECT 1').scalar_one()
            self.cursor=self.connection.execution_options(stream_results=True,max_row_buffer=self.fetch_rows).execute(self.statement())
            while batch:=self.cursor.fetchmany(self.fetch_rows):
                for row in batch:
                    if row[-1]>MAX_ROW_BYTES:raise SourceReadError('Projected source row exceeds 1 MiB.')
                    values=list(row[:-1])
                    for index,profile in enumerate(self.profiles):
                        value=values[index]
                        if value is None:continue
                        if profile['logical_type']=='boolean' and type(value) is not bool:
                            if type(value) is not int or value not in (0,1):raise SourceReadError('Source boolean contains a value other than zero or one.')
                            values[index]=bool(value)
                        if self.dialect=='mysql' and profile.get('timezone_semantics')=='aware' and isinstance(value,datetime):
                            # The MySQL session was explicitly pinned to UTC;
                            # DATETIME columns remain naive and are not changed.
                            values[index]=value.replace(tzinfo=timezone.utc)
                    # The SQL guard limits payload; this additional accounting
                    # also bounds decoded Python objects before downstream use.
                    actual=sys.getsizeof(values)+sum(sys.getsizeof(v) for v in values)
                    if actual>BUFFER_BYTES:raise SourceReadError('Decoded source row exceeds its memory buffer.')
                    yield dict(zip(self.columns,values))
            self.cursor.close();self.cursor=None
            # A locally buffered EOF cannot prove a still-live source session.
            # Fail instead of silently reconnecting after a lost snapshot.
            self.connection.execution_options(stream_results=False).exec_driver_sql('SELECT 1').scalar_one()
        except SourceReadError:raise
        except Exception as error:
            original=getattr(error,'orig',error)
            code=getattr(original,'sqlstate',None) or type(original).__name__
            raise SourceReadError('Source snapshot could not be read completely; discard the incomplete dataset. ['+code+']') from None
        finally:
            if self.cursor is not None:
                try:self.cursor.close()
                except Exception:pass
                self.cursor=None

    def __exit__(self,*error):
        if self.cursor is not None:
            try:self.cursor.close()
            except Exception:pass
            self.cursor=None
        if self.connection is not None:
            try:self.connection.rollback()
            except Exception:self.connection.invalidate()
            finally:self.connection.close();self.connection=None
