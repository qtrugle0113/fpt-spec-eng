"""T102: pagination, version identity and pause readback before controller wiring."""
import unittest
from uuid import uuid4


class DeploymentClientTests(unittest.TestCase):
    def module(self):
        from aat_api.airflow_client.deployment import DeploymentClient
        return DeploymentClient

    def test_inventory_reads_every_page_and_never_fakes_completeness(self):
        calls=[]
        class Client:
            def request(self,method,path,**kwargs):
                offset=kwargs['params']['offset'];calls.append(offset)
                return {'dags':[{'dag_id':'dag_'+str(i)} for i in range(offset,min(offset+200,205))],'total_entries':205}
        result=self.module()(Client()).dags()
        self.assertEqual(len(result),205);self.assertEqual(calls,[0,200])

    def test_version_number_is_path_identity_and_uuid_remains_metadata(self):
        calls=[];identity=str(uuid4())
        class Client:
            def request(self,method,path,**kwargs):calls.append(path);return {'id':identity,'version_number':3}
        client=self.module()(Client())
        self.assertEqual(client.version('dag/one',3)['id'],identity)
        self.assertEqual(calls,['/dags/dag%2Fone/dagVersions/3'])
        with self.assertRaises(ValueError):client.version('dag/one',identity)

    def test_pause_requires_readback_and_health_checks_component_states(self):
        from aat_api.airflow_client.client import AirflowError
        calls=[]
        class Client:
            def request(self,method,path,**kwargs):
                calls.append(method)
                return {'is_paused':False} if path!='/monitor/health' else {'metadatabase':{'status':'healthy'},'scheduler':{'status':'unhealthy'},'dag_processor':{'status':'healthy'}}
        client=self.module()(Client())
        with self.assertRaises(AirflowError):client.pause('dag',True)
        self.assertEqual(calls,['PATCH','GET'])
        with self.assertRaises(AirflowError):client.health()

    def test_import_errors_match_the_full_file_path_not_a_basename(self):
        class Client:
            def request(self,*args,**kwargs):return {'import_errors':[{'filename':'/opt/airflow/dags/a.py'},
                {'filename':'/opt/airflow/dags/external/a.py'}],'total_entries':2}
        self.assertEqual(self.module()(Client()).import_errors('/opt/airflow/dags/a.py'),[{'filename':'/opt/airflow/dags/a.py'}])
