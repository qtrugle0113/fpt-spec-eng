"""Persistent defaults with a revision covering the complete settings document."""
from sqlalchemy import select
from aat_metadata.models.settings import ApplicationSetting
from aat_api.errors import APIError
from aat_api.services.connections.service import transaction
from aat_api.services.health import probe


def project(rows):
    if len(rows)!=4:
        raise APIError('SETTINGS_UNAVAILABLE','Application settings are not initialized.',503)
    return {**{row.key:row.value_json for row in rows},
            'revision':sum(row.revision for row in rows),'application_version':'0.1.0'}


def connectivity(value):
    state=probe()['dependencies']['airflow']
    return {**value,'airflow_connectivity_status':{
        'HEALTHY':'AVAILABLE','UNHEALTHY':'UNAVAILABLE','UNKNOWN':'UNKNOWN'}[state]}


def detail():
    with transaction() as session:
        # A shared lock gives a coherent view during concurrent PATCH requests.
        rows=session.scalars(select(ApplicationSetting).order_by(ApplicationSetting.key)
                             .with_for_update(read=True)).all()
        value=project(rows)
    return connectivity(value)


def patch(expected,value):
    with transaction() as session:
        rows=session.scalars(select(ApplicationSetting).order_by(ApplicationSetting.key)
                             .with_for_update()).all()
        if project(rows)['revision']!=expected:
            raise APIError('STALE_REVISION','Settings changed. Reload before saving.',412)
        changes=value.model_dump(exclude_unset=True)
        for row in rows:
            if row.key in changes:row.value_json=changes[row.key]
        session.flush()
        # The database trigger increments each changed row's revision.
        for row in rows:session.refresh(row)
        result=project(rows)
    return connectivity(result)
