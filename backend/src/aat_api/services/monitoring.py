"""Airflow is the history authority; application metadata only supplies ownership/ETL evidence."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import json
import os
from pathlib import PurePosixPath
import re
import time
from urllib.parse import quote,urlsplit
from sqlalchemy import select,text
from aat_api.airflow_client.client import AirflowError,DeadlineTransport
from aat_api.airflow_client.monitoring import MonitoringClient
from aat_api.errors import APIError
from aat_api.logging import redact
from aat_api.services.connections.service import transaction
from aat_api.services.runtime_binding import airflow as runtime_airflow


def airflow():return MonitoringClient(DeadlineTransport(runtime_airflow().client,time.monotonic()+30))


def public_url(dag_id,run_id=None):
    origin=os.environ.get('AAT_AIRFLOW_PUBLIC_URL','http://localhost:8080').rstrip('/')
    parsed=urlsplit(origin)
    if parsed.scheme not in ('http','https') or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise APIError('AIRFLOW_PUBLIC_URL_INVALID','The public Airflow address is not configured correctly.',503)
    result=origin+'/dags/'+quote(dag_id,safe='')
    return result+('/runs/'+quote(run_id,safe='') if run_id else '')


def local_metadata():
    with transaction() as session:
        rows=session.execute(text("""SELECT e.dag_id,e.id AS definition_id,r.id AS revision_id,r.upload_id,r.config_json,r.config_sha256,
            d.id AS deployment_id,d.generated_file_key,g.generation,g.deployment_id AS gate_deployment_id,g.gate_state
            FROM etl_definitions e JOIN etl_definition_revisions r ON r.id=e.current_revision_id
            LEFT JOIN LATERAL (SELECT * FROM dag_deployments p WHERE p.etl_revision_id=r.id AND p.state='DEPLOYED'
                ORDER BY p.last_verified_at DESC,p.id DESC LIMIT 1) d ON true
            LEFT JOIN dag_admission g ON g.dag_id=e.dag_id WHERE e.owner='aat'""")).mappings().all()
        return {row['dag_id']:dict(row) for row in rows}


def managed(raw,local):
    if not local or not local['deployment_id'] or not local['generated_file_key']:return False
    tags={tag.get('name') for tag in raw.get('tags',[]) if isinstance(tag,dict)}
    expected=str(PurePosixPath(os.environ.get('AAT_AIRFLOW_DAGS_ROOT','/opt/airflow/dags'))/local['generated_file_key'])
    return {'aat','aat_revision:'+local['config_sha256']}<=tags and raw.get('fileloc')==expected


def reference(raw):
    if not raw:return None
    return dict(dag_id=raw['dag_id'],run_id=raw['dag_run_id'],start_time=raw.get('start_date'),end_time=raw.get('end_date'),
        airflow_url=public_url(raw['dag_id'],raw['dag_run_id']))


def project_dag(client,raw,local):
    if type(raw.get('is_paused')) is not bool:raise AirflowError(503)
    owned=managed(raw,local);detail=client.details(raw['dag_id'])
    latest=client.recent(raw['dag_id']);success=client.recent(raw['dag_id'],state='success')
    active=not raw['is_stale'] if type(raw.get('is_stale')) is bool else None
    if raw.get('has_import_errors') is True:active=False
    config=local['config_json'] if owned else {}
    return dict(dag_id=raw['dag_id'],description=raw.get('description'),ownership='MANAGED' if owned else 'EXTERNAL',
        is_paused=raw['is_paused'],is_active=active,schedule=config.get('schedule') if owned else raw.get('timetable_summary'),
        timezone=config.get('timezone') if owned else detail.get('timezone'),
        definition_id=local['definition_id'] if owned else None,revision_id=local['revision_id'] if owned else None,
        upload_id=local['upload_id'] if owned else None,deployment_id=local['deployment_id'] if owned else None,
        latest_run_status=latest.get('state') if latest else None,next_scheduled_run=raw.get('next_dagrun_run_after'),
        airflow_url=public_url(raw['dag_id']),last_successful_run=reference(success),last_successful_run_availability='AVAILABLE')


def inventory(*,search=None,ownership=None,paused=None,latest_status=None,limit=50,offset=0):
    client=airflow();local=local_metadata();raw=client.dags()
    if len({row['dag_id'] for row in raw})!=len(raw):raise AirflowError(503)
    selected=[row for row in raw if (not search or search.casefold() in row['dag_id'].casefold())
        and (not ownership or ('MANAGED' if managed(row,local.get(row['dag_id'])) else 'EXTERNAL')==ownership)
        and (paused is None or row.get('is_paused')==paused)]
    selected.sort(key=lambda row:row['dag_id'])
    if latest_status:
        with ThreadPoolExecutor(max_workers=4) as pool:
            states=list(pool.map(lambda row:client.recent(row['dag_id']),selected))
        selected=[row for row,state in zip(selected,states) if state and state.get('state')==latest_status]
    total=len(selected);page=selected[offset:offset+limit]
    with ThreadPoolExecutor(max_workers=4) as pool:
        items=list(pool.map(lambda row:project_dag(client,row,local.get(row['dag_id'])),page))
    return dict(items=items,total=total,next_offset=offset+len(items) if offset+len(items)<total else None)


def detail(dag_id):
    client=airflow();raw=client.dag(dag_id);local=local_metadata().get(dag_id)
    result=project_dag(client,raw,local)
    etag=str(local['generation']) if result['ownership']=='MANAGED' and local['gate_deployment_id']==local['deployment_id'] else None
    return result,etag


def duration(raw):
    value=raw.get('duration')
    if isinstance(value,(int,float)) and not isinstance(value,bool) and value>=0:return int(value*1000)
    if not raw.get('start_date'):return None
    start=datetime.fromisoformat(raw['start_date'].replace('Z','+00:00'))
    end=datetime.fromisoformat(raw['end_date'].replace('Z','+00:00')) if raw.get('end_date') else datetime.now(timezone.utc)
    return max(0,int((end-start).total_seconds()*1000))


def project_run(raw,*,with_tasks=False,client=None,owned=False):
    dag_id,run_id=raw['dag_id'],raw['dag_run_id'];metrics=None;revision=None
    if owned:
        with transaction() as session:
            row=session.execute(text("""SELECT b.id,b.etl_revision_id,b.commit_uncertain,m.extracted_rows,m.validated_rows,m.loaded_rows,
                m.failed_rows_nullable,m.staging_bytes_current,m.duration_ms,m.phase,
                (SELECT COALESCE(sum(a.bytes),0) FROM staging_artifacts a WHERE a.dataset_id=b.dataset_id AND a.recovery_protected) AS protected_bytes
                FROM execution_bindings b LEFT JOIN execution_metrics m ON m.binding_id=b.id
                WHERE b.dag_id=:dag AND b.airflow_run_id=:run"""),{'dag':dag_id,'run':run_id}).mappings().first()
            if row:
                revision=row['etl_revision_id']
                metrics=dict(extracted_rows=row['extracted_rows'],validated_rows=row['validated_rows'],loaded_rows=row['loaded_rows'],
                    failed_rows=row['failed_rows_nullable'],staging_bytes=row['staging_bytes_current'],duration_ms=row['duration_ms'],
                    phase=row['phase'],protected_bytes=row['protected_bytes'],
                    recovery_summary='Commit reconciliation required; protected staging is retained.' if row['commit_uncertain'] else None)
    tasks=[]
    if with_tasks:
        for task in client.tasks(dag_id,run_id):
            tasks.append(dict(task_id=task['task_id'],map_index=task.get('map_index',-1),state=task.get('state'),
                try_number=task.get('try_number'),start_time=task.get('start_date'),end_time=task.get('end_date'),
                duration_ms=duration(task),error_summary='Task failed. Review the redacted attempt logs.' if task.get('state')=='failed' else None))
    return dict(dag_id=dag_id,run_id=run_id,revision_id=revision,state=raw['state'],run_type=raw['run_type'],
        error_summary='The Airflow run failed. Review its task states and logs.' if raw['state']=='failed' else None,
        start_time=raw.get('start_date'),queued_time=raw.get('queued_at'),end_time=raw.get('end_date'),
        duration_ms=duration(raw),tasks=tasks,metrics=metrics)


def runs(dag_id,*,from_=None,to=None,state=None,limit=50,offset=0):
    if from_ and to and from_>to:raise APIError('INVALID_DATE_RANGE','From must not be after to.',422)
    client=airflow();raw=client.dag(dag_id);owned=managed(raw,local_metadata().get(dag_id))
    values=client.runs(dag_id,params={'order_by':'-run_after'})
    if len({row['dag_run_id'] for row in values})!=len(values):raise AirflowError(503)
    def selected(row):
        moment=row.get('start_date') or row.get('queued_at')
        stamp=datetime.fromisoformat(moment.replace('Z','+00:00')) if moment else None
        return (not state or row['state']==state) and (not from_ or stamp and stamp>=from_) and (not to or stamp and stamp<=to)
    values=[row for row in values if selected(row)];total=len(values)
    page=values[offset:offset+limit]
    return dict(items=[project_run(row,owned=owned) for row in page],total=total,
        next_offset=offset+len(page) if offset+len(page)<total else None)


def run_detail(dag_id,run_id):
    client=airflow();owned=managed(client.dag(dag_id),local_metadata().get(dag_id))
    return project_run(client.run(dag_id,run_id),with_tasks=True,client=client,owned=owned)


def log_page(dag_id,run_id,task_id,*,attempt=1,map_index=-1,token=None):
    try:page=airflow().logs(dag_id,run_id,task_id,attempt=attempt,map_index=map_index,token=token)
    except AirflowError as error:
        if error.status!=404:raise
        return dict(content=[],available=False,truncated=False,continuation_token=None,
            unavailable_reason='Logs are not available for this task attempt.')
    from aat_metadata.models.connections import ConnectionSecret
    from aat_api.services.connections.service import codec
    with transaction() as session:
        ring=codec();secrets=set();secret_bytes=0
        for row in session.scalars(select(ConnectionSecret).execution_options(yield_per=100)):
            value=ring.decrypt(row.key_id,row.ciphertext)
            if value and value not in secrets:
                secret_bytes+=len(value.encode())
                if secret_bytes>256*1024:raise APIError('LOG_REDACTION_UNAVAILABLE','Log redaction capacity exceeded. Open Airflow or contact the operator.',503)
                secrets.add(value)
    known=re.compile('|'.join(re.escape(value) for value in sorted(secrets,key=len,reverse=True))) if secrets else None
    # Account for JSON escaping and envelope fields, not only visible UTF-8 text.
    content=[];size=len(json.dumps(dict(content=[],continuation_token=page.get('continuation_token'),available=True,truncated=False,unavailable_reason=None)).encode())+256;truncated=False
    for value in page['content']:
        line=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False)
        line=re.sub(r'(?i)Bearer\s+\S+','Bearer [REDACTED]',line)
        if known:line=known.sub('[REDACTED]',line)
        line=re.sub(r"""(?i)((?:"|')?(?:password|passwd|pwd|token|secret|authorization|ciphertext)(?:"|')?\s*[:=]\s*)(?:"[^"]*"|'[^']*'|[^\s,}]+)""",r'\1"[REDACTED]"',line)
        line=redact(line)
        line=re.sub(r'(?i)([a-z][a-z0-9+.-]*://)[^/@\s]+:[^/@\s]+@',r'\1[REDACTED]@',line)
        remaining=1024**2-size;encoded=json.dumps(line,ensure_ascii=False).encode()
        if len(encoded)+1>remaining:
            low,high=0,len(line)
            while low<high:
                middle=(low+high+1)//2
                if len(json.dumps(line[:middle],ensure_ascii=False).encode())+1<=remaining:low=middle
                else:high=middle-1
            if low:content.append(line[:low])
            truncated=True;break
        content.append(line);size+=len(encoded)+1
    return dict(content=content,continuation_token=page.get('continuation_token'),available=True,truncated=truncated,
        unavailable_reason='Display limit reached. Open Airflow for the remaining log content.' if truncated else None)
