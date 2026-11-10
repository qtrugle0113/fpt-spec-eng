"""Public Airflow read models and bounded log pages; no metadata database access."""
from .client import AirflowError,segment
from .deployment import DeploymentClient


class MonitoringClient(DeploymentClient):
    def recent(self,dag_id,*,state=None):
        params={'limit':1,'offset':0,'order_by':'-end_date' if state=='success' else '-run_after'}
        if state:params['state']=state
        result=self.client.request('GET','/dags/'+segment(dag_id)+'/dagRuns',params=params)
        if not isinstance(result.get('dag_runs'),list) or type(result.get('total_entries')) is not int:
            raise AirflowError(503)
        if len(result['dag_runs'])>1 or result['total_entries']<len(result['dag_runs']):raise AirflowError(503)
        if result['total_entries']>0 and not result['dag_runs']:raise AirflowError(503,retryable=True)
        return result['dag_runs'][0] if result['dag_runs'] else None

    def logs(self,dag_id,run_id,task_id,*,attempt,map_index=-1,token=None):
        params={'map_index':map_index,'full_content':False}
        if token:params['token']=token
        result=self.client.request('GET','/dags/'+segment(dag_id)+'/dagRuns/'+segment(run_id)+
            '/taskInstances/'+segment(task_id)+'/logs/'+str(attempt),params=params)
        if not isinstance(result,dict) or not isinstance(result.get('content'),list):raise AirflowError(503)
        if result.get('continuation_token') is not None and not isinstance(result['continuation_token'],str):raise AirflowError(503)
        return result
