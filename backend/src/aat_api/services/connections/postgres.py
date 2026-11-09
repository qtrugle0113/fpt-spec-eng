"""PostgreSQL probe: pinned address, NullPool, bounded connect/query, safe results."""
import hashlib
import json
import re
import time
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool
from .policy import ConnectionPolicyError, ProbeResult, resolve_host


def classify_error(error: BaseException) -> str:
    original = getattr(error, 'orig', error)
    state = getattr(original, 'sqlstate', None)
    known = {'28P01':'AUTHENTICATION_FAILED', '28000':'AUTHENTICATION_FAILED',
             '3D000':'DATABASE_NOT_FOUND', '3F000':'SCHEMA_NOT_FOUND',
             '42501':'PERMISSION_DENIED', '57014':'TIMEOUT', '0A000':'UNSUPPORTED_DATABASE'}
    if state in known:
        return known[state]
    message = str(original).lower()
    # libpq startup failures may not expose SQLSTATE on the connection exception.
    if 'password authentication failed' in message or 'no pg_hba.conf entry' in message:
        return 'AUTHENTICATION_FAILED'
    if re.search(r'database .* does not exist',message):
        return 'DATABASE_NOT_FOUND'
    if 'timeout' in message or 'timed out' in message:
        return 'TIMEOUT'
    if 'connection refused' in message:
        return 'PORT_UNREACHABLE'
    if 'could not translate' in message or 'name or service' in message or 'network is unreachable' in message:
        return 'HOST_UNREACHABLE'
    return 'UNKNOWN_DATABASE_ERROR'


def test_connection(config: dict, password: str) -> ProbeResult:
    started = time.monotonic()
    engine = None
    def failed(code: str) -> ProbeResult:
        return ProbeResult('FAILED', int((time.monotonic()-started)*1000), code=code)
    try:
        address = resolve_host(config['host'], config['port'])[0]
        url = URL.create('postgresql+psycopg', username=config['username'], password=password,
                         host=config['host'], port=config['port'], database=config['database_name'],
                         query={'hostaddr':address, 'connect_timeout':'10'})
        engine = create_engine(url, poolclass=NullPool, hide_parameters=True,
                               connect_args={'options':'-c statement_timeout=5000 -c lock_timeout=3000'})
        with engine.connect() as connection:
            identity = connection.execute(text("SELECT inet_server_addr()::text, inet_server_port(), oid::text, current_setting('server_version_num') FROM pg_database WHERE datname=current_database()")).one()
            schema = config.get('schema_name') or 'public'
            exists = connection.execute(text("SELECT has_schema_privilege(oid,'USAGE') FROM pg_namespace WHERE nspname=:schema"), {'schema':schema}).first()
            if exists is None:
                return failed('SCHEMA_NOT_FOUND')
            if not exists[0]:
                return failed('PERMISSION_DENIED')
            fingerprint = hashlib.sha256(json.dumps(['POSTGRESQL', *identity[:3]], separators=(',',':')).encode()).hexdigest()
            return ProbeResult('SUCCESS', int((time.monotonic()-started)*1000), server_fingerprint=fingerprint,
                               capabilities={'server_version':identity[3], 'schema_usage':True})
    except ConnectionPolicyError as error:
        return failed(error.code)
    except (SQLAlchemyError, OSError) as error:
        return failed(classify_error(error))
    finally:
        if engine is not None:
            engine.dispose()
