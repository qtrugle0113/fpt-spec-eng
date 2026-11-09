from uuid import uuid4
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from tests.integration import test_t023_models as auth


class OperationModelTests(auth.AuthorizationModelTests):
    def operation(self,**changes):
        values=dict(kind='TABLE_CREATE',idempotency_key=str(uuid4()),request_sha256='a'*64)
        values.update(changes);row=self.operations.Operation(**values)
        self.session.add(row);self.session.flush();return row

    def test_operation_key_state_count_and_progress(self):
        row=self.operation();self.assertEqual(row.state,'QUEUED')
        for changes in [dict(idempotency_key=row.idempotency_key),dict(state='DONE'),dict(attempt=-1),dict(progress_json={'password':'raw'})]:
            with self.subTest(changes=changes),self.assertRaises(IntegrityError),self.session.begin_nested(): self.operation(**changes)

    def test_job_requires_validated_upload_and_result_fk(self):
        _,upload=self.upload(status='UPLOADED');parent=self.connection_row();rev,_=self.revision(parent)
        op=self.operation()
        with self.assertRaises(IntegrityError),self.session.begin_nested():
            self.session.add(self.operations.TableCreationJob(operation_id=op.id,upload_id=upload.id,
                target_revision_id=rev.id,confirmation_hash='a'*64));self.session.flush()

    def test_operation_state_graph_rejects_terminal_replay(self):
        op=self.operation();op.state='RUNNING';self.session.flush();op.state='NEEDS_RECONCILIATION';self.session.flush()
        with self.assertRaises(IntegrityError),self.session.begin_nested():
            op.state='QUEUED';self.session.flush()

    def test_active_deployment_unique_across_revisions_of_same_dag(self):
        parent,rev=self.etl_revision()
        second=self.etl.ETLDefinitionRevision(definition_id=parent.id,revision=2,upload_id=rev.upload_id,
            config_json={'load_strategy':'UPSERT'},status='DRAFT')
        self.session.add(second);self.session.flush()
        first=self.operations.DAGDeployment(operation_id=self.operation(kind='DEPLOY').id,
            etl_revision_id=rev.id,state='DEPLOYMENT_PENDING',revision_sha256=rev.config_sha256)
        self.session.add(first);self.session.flush()
        with self.assertRaises(IntegrityError),self.session.begin_nested():
            self.session.add(self.operations.DAGDeployment(operation_id=self.operation(kind='DEPLOY').id,
                etl_revision_id=second.id,state='DEPLOYMENT_PENDING',revision_sha256=second.config_sha256));self.session.flush()
        first.state='DEPLOYMENT_FAILED';self.session.flush()
        with self.assertRaises(IntegrityError),self.session.begin_nested():first.state='DEPLOYMENT_PENDING';self.session.flush()

    def test_audit_rejects_raw_error_and_nested_credential(self):
        for summary,scope in [('postgresql://user:password@host',{}),('safe.event',{'payload':{'password':'secret'}})]:
            with self.assertRaises(IntegrityError),self.session.begin_nested():
                self.session.add(self.operations.AuditEvent(subject_type='operation',subject_id=uuid4(),action='failed',
                    safe_summary=summary,acknowledgment_scope=scope));self.session.flush()

