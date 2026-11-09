from sqlalchemy.exc import IntegrityError
from tests.integration import test_t025_models as runtime


class ReplacementModelTests(runtime.RuntimeModelTests):
    def admission(self,b,**changes):
        values=dict(binding_id=b.id,run_intent_id=b.run_intent_id,authorization_id=b.authorization_id,
            admission_epoch=1,authorization_revision=1,scope_sha256='a'*64,dataset_sha256='b'*64,
            target_identity='c'*64,owner_process_id='writer',target_session_identity='session')
        values.update(changes);row=self.replacement_runs.ReplacementAdmission(**values)
        self.session.add(row);self.session.flush();return row

    def test_only_one_unreconciled_admission_per_binding_and_identity_immutable(self):
        b=self.binding();a=self.admission(b)
        with self.assertRaises(IntegrityError),self.session.begin_nested():self.admission(b,admission_epoch=2)
        with self.assertRaises(IntegrityError),self.session.begin_nested():a.owner_process_id='other';self.session.flush()
        a.state='ROLLBACK_VERIFIED';self.session.flush();self.admission(b,admission_epoch=2)

    def test_reserved_once_cannot_release_pointer_or_reuse_grant(self):
        b=self.binding();a=self.session.get(self.authorizations.DataReplacementAuthorization,b.authorization_id)
        a.reserved_intent_id=b.run_intent_id;a.state='RESERVED';self.session.flush()
        with self.assertRaises(IntegrityError),self.session.begin_nested():a.reserved_intent_id=None;self.session.flush()
        with self.assertRaises(IntegrityError),self.session.begin_nested():a.state='GRANTED';self.session.flush()
