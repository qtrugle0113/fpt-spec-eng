"""Airflow 3.3.2 deployment/control reads; no application state is inferred."""
from uuid import UUID
from pathlib import PurePosixPath
from .client import AirflowError,segment


class DeploymentClient:
    def __init__(self,client):self.client=client

    def pages(self,path,key,*,params=None):
        offset=0;items=[];expected=None
        while True:
            payload=self.client.request('GET',path,params={**(params or {}),'limit':200,'offset':offset})
            if not isinstance(payload,dict) or not isinstance(payload.get(key),list) or type(payload.get('total_entries')) is not int:
                raise AirflowError(503)
            total=payload['total_entries'];page=payload[key]
            if total<0 or expected is not None and total!=expected or len(page)>200 or offset+len(page)>total:
                raise AirflowError(503,retryable=True)
            expected=total;items.extend(page);offset+=len(page)
            if offset==total:return items
            if not page:raise AirflowError(503,retryable=True)

    def dags(self):return self.pages('/dags','dags')
    def dag(self,dag_id):return self.client.request('GET','/dags/'+segment(dag_id))
    def details(self,dag_id):
        result=self.client.request('GET','/dags/'+segment(dag_id)+'/details')
        version=result.get('latest_dag_version')
        if version is not None:self._version(version)
        return result

    def versions(self,dag_id):return self.pages('/dags/'+segment(dag_id)+'/dagVersions','dag_versions')
    def version(self,dag_id,number):
        if type(number) is not int or number<1:raise ValueError('A positive Airflow version number is required.')
        result=self.client.request('GET','/dags/'+segment(dag_id)+'/dagVersions/'+str(number))
        self._version(result)
        if result['version_number']!=number:raise AirflowError(503)
        return result

    @staticmethod
    def _version(value):
        try:
            UUID(value['id'])
            if type(value['version_number']) is not int or value['version_number']<1:raise ValueError()
        except (KeyError,TypeError,ValueError,AttributeError):raise AirflowError(503) from None

    def import_errors(self,fileloc=None):
        errors=self.pages('/importErrors','import_errors')
        if fileloc is None:return errors
        return [error for error in errors if isinstance(error.get('filename'),str) and PurePosixPath(error['filename'])==PurePosixPath(fileloc)]
    def runs(self,dag_id,*,params=None):return self.pages('/dags/'+segment(dag_id)+'/dagRuns','dag_runs',params=params)
    def run(self,dag_id,run_id):
        result=self.client.request('GET','/dags/'+segment(dag_id)+'/dagRuns/'+segment(run_id))
        if not isinstance(result.get('dag_versions'),list):raise AirflowError(503)
        for version in result['dag_versions']:self._version(version)
        return result

    def tasks(self,dag_id,run_id):
        return self.pages('/dags/'+segment(dag_id)+'/dagRuns/'+segment(run_id)+'/taskInstances','task_instances')

    def task(self,dag_id,run_id,task_id):
        result=self.client.request('GET','/dags/'+segment(dag_id)+'/dagRuns/'+segment(run_id)+'/taskInstances/'+segment(task_id),params={'map_index':-1})
        if result.get('dag_version') is not None:self._version(result['dag_version'])
        return result

    def pause(self,dag_id,paused):
        if type(paused) is not bool:raise ValueError('Pause state must be a boolean.')
        self.client.request('PATCH','/dags/'+segment(dag_id),json={'is_paused':paused})
        actual=self.dag(dag_id)
        if actual.get('is_paused') is not paused:raise AirflowError(409,retryable=True)
        return actual

    def health(self):
        health=self.client.request('GET','/monitor/health')
        if any(health.get(name,{}).get('status')!='healthy' for name in ('metadatabase','scheduler','dag_processor')):
            raise AirflowError(503,retryable=True)
        return health
