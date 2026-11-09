"""Foundation readiness with real app DB/head/key/worker and Airflow probes."""
import json
import os
from pathlib import Path
import urllib.request
from aat_api.workers.main import connect
from aat_api.logging import logger
from aat_metadata.secrets.codec import SecretCodec


def probe():
    dependencies={k:'UNKNOWN' for k in ('application_database','migration_head','encryption_keys','worker','airflow')}
    try:
        with connect() as c:
            dependencies['application_database']='HEALTHY' if c.execute('SELECT current_database()').fetchone()[0]=='app_metadata' else 'UNHEALTHY'
            heads=c.execute('SELECT version_num FROM alembic_version').fetchall()
            dependencies['migration_head']='HEALTHY' if heads==[('0001_metadata',)] else 'UNHEALTHY'
            dependencies['worker']='HEALTHY' if c.execute("SELECT EXISTS(SELECT 1 FROM worker_heartbeats WHERE heartbeat_at>now()-interval '20 seconds')").fetchone()[0] else 'UNHEALTHY'
            codec=SecretCodec(Path(os.environ.get('AAT_APP_KEYRING','/secrets/app_keyring')))
            for key_id,ciphertext in c.execute('SELECT DISTINCT ON(key_id) key_id,ciphertext FROM connection_secrets ORDER BY key_id'):
                codec.decrypt(key_id,ciphertext)
            dependencies['encryption_keys']='HEALTHY'
    except Exception as exc:
        logger.warning('foundation_database_probe_failed exception_type=%s',type(exc).__name__)
        # Preserve resolved checks, unknown checks remain fail-closed.
    if dependencies['application_database']!='HEALTHY':
        return {'ready':False,'dependencies':dependencies}
    try:
        endpoint=os.environ.get('AAT_AIRFLOW_HEALTH_URL','http://airflow-apiserver:8080/api/v2/monitor/health')
        with urllib.request.urlopen(endpoint,timeout=3) as response:payload=json.load(response)
        dependencies['airflow']='HEALTHY' if all(payload.get(k,{}).get('status')=='healthy' for k in ('metadatabase','scheduler','dag_processor')) else 'UNHEALTHY'
    except Exception as exc:
        dependencies['airflow']='UNHEALTHY'
        logger.warning('foundation_airflow_probe_failed exception_type=%s',type(exc).__name__)
    return {'ready':all(v=='HEALTHY' for v in dependencies.values()),'dependencies':dependencies}
