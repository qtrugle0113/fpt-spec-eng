from uuid import uuid4
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from tests.integration import test_t024_models as operations


class RuntimeModelTests(operations.OperationModelTests):
    def binding(self,file_parser_revision=None):
        authorization=self.authorization();op=self.operation(kind='DAG_TRIGGER')
        intent=self.replacement_runs.RunIntent(operation_id=op.id,run_uuid=uuid4(),dag_id=authorization.dag_id,
            airflow_run_id='manual__'+uuid4().hex,run_type='manual',etl_revision_id=authorization.etl_revision_id,
            authorization_id=authorization.id,request_sha256='b'*64)
        self.session.add(intent);self.session.flush()
        parent=self.connection_row();rev,_=self.revision(parent)
        binding=self.runtime.ExecutionBinding(dag_id=authorization.dag_id,airflow_run_id=intent.airflow_run_id,
            task_id='transfer',airflow_dag_version_id=str(uuid4()),etl_revision_id=authorization.etl_revision_id,
            source_revision_id=rev.id,target_revision_id=rev.id,run_intent_id=intent.id,airflow_run_type='manual',
            authorization_id=authorization.id,runtime_build='tests',binding_hash='c'*64,file_parser_revision=file_parser_revision)
        self.session.add(binding);self.session.flush();return binding

    def test_binding_identity_immutable_and_counts_nonnegative(self):
        b=self.binding()
        with self.assertRaises(IntegrityError),self.session.begin_nested():
            b.binding_hash='d'*64;self.session.flush()
        with self.assertRaises(IntegrityError),self.session.begin_nested():
            self.session.add(self.runtime.ExecutionMetric(binding_id=b.id,extracted_rows=-1));self.session.flush()

    def test_complete_manifest_immutable_and_artifact_path_safe(self):
        b=self.binding();m=self.runtime.DatasetManifest(execution_binding_id=b.id,generation=1,
            schema_hash='a'*64,mapping_hash='b'*64,path_key='fixture/'+uuid4().hex,manifest_sha256='c'*64,
            extracted_rows=2,validated_rows=2,total_bytes=4,state='COMPLETE')
        self.session.add(m);self.session.flush()
        with self.assertRaises(IntegrityError),self.session.begin_nested():m.total_bytes=5;self.session.flush()
        with self.assertRaises(IntegrityError),self.session.begin_nested():
            self.session.add(self.runtime.StagingArtifact(dataset_id=m.id,attempt_id=uuid4(),path_key='../escape',
                file_ordinal=1,file_sha256='d'*64,rows=1,bytes=1));self.session.flush()

    def test_binding_cannot_replace_complete_dataset_pointer(self):
        b=self.binding()
        first=self.runtime.DatasetManifest(execution_binding_id=b.id,generation=1,schema_hash='a'*64,
            mapping_hash='b'*64,path_key='fixture/'+uuid4().hex,manifest_sha256='c'*64,state='COMPLETE')
        second=self.runtime.DatasetManifest(execution_binding_id=b.id,generation=2,schema_hash='a'*64,
            mapping_hash='b'*64,path_key='fixture/'+uuid4().hex,manifest_sha256='d'*64,state='COMPLETE')
        self.session.add_all([first,second]);self.session.flush();b.dataset_id=first.id;self.session.flush()
        with self.assertRaises(IntegrityError),self.session.begin_nested():b.dataset_id=second.id;self.session.flush()

    def test_complete_manifest_cannot_reopen_and_mutate(self):
        b=self.binding();m=self.runtime.DatasetManifest(execution_binding_id=b.id,generation=1,
            schema_hash='a'*64,mapping_hash='b'*64,path_key='fixture/'+uuid4().hex,manifest_sha256='c'*64,state='COMPLETE')
        self.session.add(m);self.session.flush()
        with self.assertRaises(IntegrityError),self.session.begin_nested():m.state='INCOMPLETE';self.session.flush()

    def test_binding_retains_old_parser_after_file_advances(self):
        from aat_metadata.models.file_parsers import FileParserRevision
        file=self.defs.UploadedFile(original_name='bound.csv',extension='.csv',sha256='a'*64,bytes=4,
            encoding='utf-8',delimiter=',',header_present=True,quote_char='"',null_token='\\N')
        self.session.add(file);self.session.flush()
        old=FileParserRevision(file_id=file.id,revision=1,encoding='utf-8',delimiter=',',header_present=True,quote_char='"',null_token='\\N')
        new=FileParserRevision(file_id=file.id,revision=2,encoding='utf-8',delimiter=';',header_present=True,quote_char='"',null_token='\\N')
        self.session.add_all([old,new]);self.session.flush();file.parser_revision=2;self.session.flush()
        b=self.binding(file_parser_revision=old.id)
        self.assertEqual(b.file_parser_revision,old.id)
        with self.assertRaises(IntegrityError),self.session.begin_nested():self.session.execute(text('DELETE FROM file_parser_revisions WHERE id=:id'),{'id':old.id})

