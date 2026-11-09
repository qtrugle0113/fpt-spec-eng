"""MySQL probe: pinned numeric address, bounded driver I/O, no DSN in results."""
import hashlib
import time
import pymysql
from .policy import ConnectionPolicyError, ProbeResult, resolve_host


def classify_error(error: BaseException) -> str:
    number = error.args[0] if error.args else None
    message = str(error).lower()
    if number in (2003,2006,2013) and ('timed out' in message or 'timeout' in message):
        return 'TIMEOUT'
    known = {1045:'AUTHENTICATION_FAILED', 1049:'DATABASE_NOT_FOUND', 1044:'PERMISSION_DENIED',
             1142:'PERMISSION_DENIED', 1143:'PERMISSION_DENIED', 1227:'PERMISSION_DENIED',
             2005:'HOST_UNREACHABLE', 2006:'CONNECTION_LOST', 2013:'CONNECTION_LOST', 2026:'TLS_ERROR'}
    if number in known:
        return known[number]
    if 'timed out' in message or 'timeout' in message:
        return 'TIMEOUT'
    if number == 2003:
        return 'PORT_UNREACHABLE' if 'refused' in message else 'HOST_UNREACHABLE'
    return 'UNKNOWN_DATABASE_ERROR'


def test_connection(config: dict, password: str) -> ProbeResult:
    started = time.monotonic()
    def failed(code: str) -> ProbeResult:
        return ProbeResult('FAILED', int((time.monotonic()-started)*1000), code=code)
    try:
        address = resolve_host(config['host'], config['port'])[0]
        with pymysql.connect(host=address, port=config['port'], user=config['username'], password=password,
                             database=config['database_name'], charset='utf8mb4', autocommit=True,
                             connect_timeout=10, read_timeout=5, write_timeout=5) as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT @@server_uuid, @@version, @@default_storage_engine, @@collation_database')
                identity, version, storage, collation = cursor.fetchone()
            if not identity:
                return failed('SERVER_IDENTITY_UNAVAILABLE')
            fingerprint = hashlib.sha256(('MYSQL:'+identity).encode()).hexdigest()
            return ProbeResult('SUCCESS', int((time.monotonic()-started)*1000), server_fingerprint=fingerprint,
                               capabilities={'server_version':version, 'default_engine':storage, 'collation':collation})
    except ConnectionPolicyError as error:
        return failed(error.code)
    except (pymysql.Error, OSError) as error:
        return failed(classify_error(error))
