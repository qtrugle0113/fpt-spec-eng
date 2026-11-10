"""T118: redeploy real generated DAGs and reject cleared old run bindings."""
import io
import time
from uuid import UUID,uuid4
from openpyxl import load_workbook
from sqlalchemy import text
from tests.airflow.test_execution import WorkflowFixture


class RevisionLifecycleTests(WorkflowFixture):
    def test_new_revision_registers_and_old_clear_cannot_write_again(self):
        from aat_api.services.connections.service import transaction
        from aat_api.services.definition_uploads import storage
        from aat_api.services.etl_preview import preview
        from aat_api.services.etl_validation import execute as validate
        from aat_api.services.runtime_binding import airflow
        from aat_api.services.table_preview import target_engine
        from aat_api.workers import deployments
        context=self.workflow()
        dag=context['dag'];client=airflow()
        prior=client.details(dag)['latest_dag_version']
        with transaction() as session:
            key=session.scalar(text('SELECT f.safe_storage_key FROM definition_uploads u JOIN uploaded_files f ON f.id=u.uploaded_file_id WHERE u.id=:id'),{'id':UUID(context['upload']['id'])})
        with (storage()/key).open('rb') as stream:book=load_workbook(stream)
        book['ETL_Definitions']['Q2']=1
        data=io.BytesIO();book.save(data);book.close()
        uploaded=self.response(self.client.post('/api/v1/definition-uploads',data={'kind':'ETL'},
            files={'file':('new-revision.xlsx',data.getvalue(),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}),
            'post','/definition-uploads',201)
        command=self.response(self.client.post('/api/v1/definition-uploads/'+uploaded['id']+'/validate',headers={'Idempotency-Key':str(uuid4())},
            json={'expected_sha256':uploaded['sha256']}),'post','/definition-uploads/{id}/validate',202)
        self.assertEqual(validate(self.claim(command,'revision-validate'),'revision-validate'),('SUCCEEDED',None));self.finish(command)
        current=preview(UUID(uploaded['id']));revision=current['items'][0]['id']
        self.assertNotEqual(revision,context['item']['id'])
        command=self.response(self.client.post('/api/v1/dag-deployments',headers={'Idempotency-Key':str(uuid4())},json={
            'upload_id':uploaded['id'],'dag_ids':[dag],'confirmation_token':current['confirmation_token'],'support_objects_acknowledged':True}),
            'post','/dag-deployments',202)
        self.assertEqual(deployments.execute(self.claim(command,'revision-deploy'),'revision-deploy'),('SUCCEEDED',None));self.finish(command)
        latest=client.details(dag)['latest_dag_version']
        self.assertNotEqual(latest['id'],prior['id'])
        self.assertGreater(latest['version_number'],prior['version_number'])
        self.assertTrue(client.dag(dag)['is_paused'])
        # Ask the real public API to clear the existing run onto the new bundle.
        # Its immutable old binding must not become authority for the new revision.
        from aat_api.airflow_client.client import segment
        client.client.request('POST','/dags/'+segment(dag)+'/dagRuns/'+segment(context['run_id'])+'/clear',
            json={'dry_run':False,'only_failed':False,'run_on_latest_version':True})
        client.pause(dag,False)
        self.addCleanup(lambda:client.pause(dag,True))
        deadline=time.monotonic()+180
        while True:
            actual=client.run(dag,context['run_id'])
            if actual['state']=='failed':break
            if time.monotonic()>deadline:self.fail('Cleared old run was not rejected by the new revision')
            time.sleep(1)
        with target_engine(context['target_revision']) as engine,engine.connect() as connection:
            self.assertEqual(list(connection.execute(text('SELECT id,note FROM '+context['target']+' ORDER BY id'))),[(1,'first'),(2,None)])
        with transaction() as session:
            bindings=session.execute(text('SELECT etl_revision_id,state,commit_uncertain FROM execution_bindings WHERE dag_id=:dag'),{'dag':dag}).all()
            self.assertEqual([tuple(row) for row in bindings],[(UUID(context['item']['id']),'COMMIT_VERIFIED',False)])
        print('REVISION_LIFECYCLE_VERIFIED new_version=true old_clear_failed=true target_unchanged=true',flush=True)
