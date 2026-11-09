"""Explicit app DB connection configuration and independent session ownership."""
from contextlib import contextmanager
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session


def database_url(owner=False,runtime=False):
    if owner and runtime:raise ValueError('Choose one metadata role')
    if os.environ.get('AAT_FOUNDATION_DISPOSABLE')=='1':
        dsn=os.environ.get('AAT_FOUNDATION_TEST_DSN')
        if not dsn:raise RuntimeError('Explicit disposable DSN required')
        from sqlalchemy.engine import make_url
        url=make_url(dsn).set(drivername='postgresql+psycopg')
        if url.database!='app_metadata':raise RuntimeError('Application database must be app_metadata')
        return url
    root=Path(os.environ.get('AAT_APP_OWNER_SECRETS','/secrets/app-owner')) if owner else Path(os.environ.get('AAT_BACKEND_SECRETS','/secrets/backend'))
    if runtime:
        root=Path(os.environ.get('AAT_RUNTIME_SECRETS','/secrets/runtime'))
        return URL.create('postgresql+psycopg',username='aat_etl',password=(root/'pg_etl').read_text(),host='postgres',database='app_metadata')
    return URL.create('postgresql+psycopg',username='aat_app_owner' if owner else 'aat_app_runtime',
        password=(root/('app_owner' if owner else 'app_runtime')).read_text(),host='postgres',database='app_metadata')


def create_app_engine(owner=False,runtime=False):
    return create_engine(database_url(owner,runtime),hide_parameters=True,pool_pre_ping=True,pool_size=2,max_overflow=2,
                         connect_args={'connect_timeout':5,'options':'-c timezone=UTC -c statement_timeout=10000 -c lock_timeout=5000'})


@contextmanager
def metadata_session(engine):
    # Each caller/runtime opens its own transaction, never shares a request session.
    with Session(engine,expire_on_commit=False) as session:
        with session.begin():yield session
