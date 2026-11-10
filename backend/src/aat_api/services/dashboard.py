"""Stream public Airflow history into bounded aggregates; never mirror run history."""
from collections import OrderedDict
from copy import deepcopy
from datetime import date,datetime,time as day_time,timedelta,timezone
import threading
import time
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
from sqlalchemy import text
from aat_api.airflow_client.client import AirflowError
from aat_api.errors import APIError
from aat_api.services.connections.service import transaction
from aat_api.services.monitoring import airflow,local_metadata,managed,public_url,reference,project_run
from .schedule_statistics import GROUPS,group

_cache=OrderedDict();_lock=threading.Lock()
MAX_HISTORY=100000


def clear_cache():
    with _lock:_cache.clear()


def counts(rows):
    result=dict(total=0,successful=0,failed=0,running=0,queued=0,other=0,success_rate=None)
    for row in rows:
        state=row.get('state');key='successful' if state=='success' else state if state in ('failed','running','queued') else 'other'
        result['total']+=1;result[key]+=1
    denominator=result['successful']+result['failed']
    if denominator:result['success_rate']=result['successful']/denominator*100
    return result


def _merge(result,row):
    key='successful' if row.get('state')=='success' else row.get('state') if row.get('state') in ('failed','running','queued') else 'other'
    result['total']+=1;result[key]+=1


def _finish(result):
    denominator=result['successful']+result['failed'];result['success_rate']=result['successful']/denominator*100 if denominator else None
    return result


def run_time(row):
    value=row.get('start_date') or row.get('queued_at') or row.get('created_at')
    try:
        parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo is not None else None
    except (ValueError,AttributeError,TypeError):return None


def date_window(first,last,zone):
    try:
        tz=ZoneInfo(zone);today=datetime.now(tz).date()
        begin=date.fromisoformat(first) if first else today-timedelta(days=6)
        finish=date.fromisoformat(last) if last else today
        if begin>finish or (finish-begin).days>=366:raise ValueError()
        return (datetime.combine(begin,day_time.min,tzinfo=tz).astimezone(timezone.utc),
            datetime.combine(finish+timedelta(days=1),day_time.min,tzinfo=tz).astimezone(timezone.utc))
    except (ValueError,OverflowError,ZoneInfoNotFoundError,TypeError):
        raise APIError('INVALID_DASHBOARD_RANGE','Use valid inclusive calendar dates (at most 366 days) and an IANA timezone.',422) from None


def _defaults():
    with transaction() as session:
        rows=dict(session.execute(text("SELECT key,value_json FROM application_settings WHERE key IN ('default_timezone','dashboard_refresh_interval')")).all())
    return rows.get('default_timezone','UTC'),min(30,int(rows.get('dashboard_refresh_interval',30)))


def _history(client):
    offset=0;expected=None
    while True:
        payload=client.client.request('GET','/dags/~/dagRuns',params={'limit':200,'offset':offset,'order_by':'-run_after'})
        if not isinstance(payload,dict):raise AirflowError(503)
        total=payload.get('total_entries');page=payload.get('dag_runs')
        if type(total) is not int or total<0 or total>MAX_HISTORY or not isinstance(page,list) or len(page)>200:
            raise AirflowError(503)
        if expected is not None and expected!=total or offset+len(page)>total:raise AirflowError(503,retryable=True)
        expected=total
        if any(not isinstance(row,dict) or not all(isinstance(row.get(key),str) for key in ('dag_id','dag_run_id','state','run_type')) for row in page):raise AirflowError(503)
        if page:yield page
        offset+=len(page)
        if offset==total:return
        if not page:raise AirflowError(503,retryable=True)


def _historical_schedules(page):
    from sqlalchemy import select,tuple_
    from aat_metadata.models.replacement_runs import RunIntent
    from aat_metadata.models.runtime import ExecutionBinding
    from aat_metadata.models.etl import ETLDefinitionRevision
    pairs=[(row['dag_id'],row['dag_run_id']) for row in page];result={}
    with transaction() as session:
        for model in (RunIntent,ExecutionBinding):
            rows=session.execute(select(model.dag_id,model.airflow_run_id,ETLDefinitionRevision.config_json)
                .join(ETLDefinitionRevision,ETLDefinitionRevision.id==model.etl_revision_id)
                .where(tuple_(model.dag_id,model.airflow_run_id).in_(pairs)))
            for dag,run,config in rows:result[(dag,run)]=config.get('schedule')
    return result


def _unavailable(start,end,zone,scope,*,inventory=None,fields=None):
    return dict(inventory=inventory or dict(total=None,active=None,paused=None,other=None),
        run_metrics={key:None for key in counts([])},lifetime_metrics={key:None for key in counts([])},
        schedule_groups=[],time_series=[],recent_runs=[],last_successful_run=None,
        last_successful_run_availability='UNKNOWN' if inventory else 'UNAVAILABLE',
        timezone=zone,scope=scope,**{'from':start.isoformat(),'to':end.isoformat()},
        next_scheduled_runs=[],completeness='INCOMPLETE' if inventory else 'UNAVAILABLE',
        unavailable_fields=fields or ['inventory','run_history','run_metrics','lifetime_metrics'],fetched_at=None,stale=False)


def snapshot(*,from_=None,to=None,zone=None,scope='ALL',force_refresh=False):
    if scope not in ('ALL','MANAGED','EXTERNAL'):raise APIError('INVALID_DASHBOARD_SCOPE','Select ALL, MANAGED or EXTERNAL scope.',422)
    default_zone,ttl=_defaults();zone=zone or default_zone;start,end=date_window(from_,to,zone);tz=ZoneInfo(zone)
    key=(start.isoformat(),end.isoformat(),zone,scope)
    with _lock:prior=_cache.get(key)
    if prior and not force_refresh and time.monotonic()-prior[0]<ttl:return deepcopy(prior[1])
    try:
        client=airflow();raw_dags=client.dags();local=local_metadata()
        if len({row['dag_id'] for row in raw_dags})!=len(raw_dags):raise AirflowError(503)
        owned={row['dag_id'] for row in raw_dags if managed(row,local.get(row['dag_id']))}
        selected=lambda identity:scope=='ALL' or (identity in owned if scope=='MANAGED' else identity not in owned)
        dags=[row for row in raw_dags if selected(row['dag_id'])]
        inventory=dict(total=len(dags),active=0,paused=0,other=0)
        groups={name:dict(group=name,dag_count=0,run_count=0) for name in GROUPS};missing=set();next_runs=[]
        for row in dags:
            if row.get('is_paused') is True:inventory['paused']+=1
            elif row.get('is_paused') is False and row.get('is_stale') is False and row.get('has_import_errors') is False:inventory['active']+=1
            else:inventory['other']+=1
            schedule=local[row['dag_id']]['config_json'].get('schedule') if row['dag_id'] in owned else row.get('timetable_summary')
            category=group(schedule);groups[category]['dag_count']+=1
            if category=='Unknown':missing.add('current_schedule')
            if row.get('next_dagrun_run_after'):
                next_runs.append(dict(dag_id=row['dag_id'],scheduled_time=row['next_dagrun_run_after'],is_paused=row['is_paused'],airflow_url=public_url(row['dag_id'])))
    except AirflowError:
        result=_unavailable(start,end,zone,scope)
        if prior:
            result=deepcopy(prior[1]);result.update(completeness='UNAVAILABLE',stale=True,unavailable_fields=['inventory','run_history','run_metrics','lifetime_metrics'])
        return result
    lifetime=counts([]);filtered=counts([]);series={};recent=[];last_success=None;last_success_time=None;unknown_success=False;seen=set()
    current=start.astimezone(tz).date();last=end.astimezone(tz).date()
    while current<last:series[current.isoformat()]=counts([]);current+=timedelta(days=1)
    try:
        for page in _history(client):
            historical=_historical_schedules(page)
            for row in page:
                identity=(row['dag_id'],row['dag_run_id'])
                if identity in seen:raise AirflowError(503,retryable=True)
                seen.add(identity)
                if not selected(row['dag_id']):continue
                _merge(lifetime,row);stamp=run_time(row)
                if row.get('state')=='success':
                    success_time=run_time({'start_date':row.get('end_date')}) or stamp
                    if success_time is None:unknown_success=True
                    elif last_success_time is None or success_time>last_success_time:last_success,last_success_time=row,success_time
                if stamp is None:missing.add('run_time_basis');continue
                if not start<=stamp<end:continue
                _merge(filtered,row);_merge(series[stamp.astimezone(tz).date().isoformat()],row)
                category=group(historical.get(identity));groups[category]['run_count']+=1
                if category=='Unknown':missing.add('historical_schedule')
                recent.append((stamp,row));recent.sort(key=lambda value:value[0],reverse=True);del recent[20:]
    except AirflowError:
        result=_unavailable(start,end,zone,scope,inventory=inventory,fields=['run_history','run_metrics','lifetime_metrics','historical_schedule'])
        if prior:
            result=deepcopy(prior[1]);result.update(inventory=inventory,completeness='INCOMPLETE',stale=True,unavailable_fields=['run_history','run_metrics','lifetime_metrics','historical_schedule'])
        return result
    _finish(lifetime);_finish(filtered)
    for metrics in series.values():_finish(metrics)
    if 'run_time_basis' in missing:
        filtered={key:None for key in filtered};series={day:{key:None for key in value} for day,value in series.items()}
        for value in groups.values():value['run_count']=None
        missing.update(('run_metrics','time_series','schedule_groups.run_count'))
    result=dict(inventory=inventory,run_metrics=filtered,lifetime_metrics=lifetime,schedule_groups=list(groups.values()),
        time_series=[dict(date=day,metrics=value) for day,value in series.items()],
        # Dashboard needs native run facts; detailed ETL evidence is loaded only
        # when the operator opens Monitoring, avoiding a metadata N+1 query.
        recent_runs=[project_run(row) for _,row in recent],
        last_successful_run=None if unknown_success else reference(last_success),
        last_successful_run_availability='UNKNOWN' if unknown_success else 'AVAILABLE',
        timezone=zone,scope=scope,**{'from':start.isoformat(),'to':end.isoformat()},
        next_scheduled_runs=sorted(next_runs,key=lambda row:row['scheduled_time'])[:20],
        completeness='INCOMPLETE' if missing else 'COMPLETE',unavailable_fields=sorted(missing),
        fetched_at=datetime.now(timezone.utc).isoformat(),stale=False)
    with _lock:
        _cache[key]=(time.monotonic(),deepcopy(result));_cache.move_to_end(key)
        while len(_cache)>32:_cache.popitem(last=False)
    return result
