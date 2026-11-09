import importlib
import os
import unittest
from uuid import uuid4
import psycopg


class OperationServiceTests(unittest.TestCase):
    def setUp(self):
        try:
            self.module=importlib.import_module('aat_api.services.operations')
            self.confirmation=importlib.import_module('aat_api.services.confirmation')
        except ModuleNotFoundError as exc:
            if not exc.name.startswith('aat_api.services.'):raise
            raise AssertionError('T033 operation/confirmation implementation missing') from None
        self.c=psycopg.connect(os.environ['AAT_FOUNDATION_TEST_DSN']);self.addCleanup(self.c.close)
        self.repo=self.module.Operations(self.c)

    def test_idempotency_replay_and_conflict(self):
        key=str(uuid4());first=self.repo.enqueue('VALIDATE',key,'a'*64)
        self.assertEqual(self.repo.enqueue('VALIDATE',key,'a'*64)['id'],first['id'])
        with self.assertRaises(ValueError),self.c.transaction():self.repo.enqueue('VALIDATE',key,'b'*64)
        self.c.rollback()

    def test_confirmation_hash_scope_expiry_and_signature(self):
        signer=self.confirmation.ConfirmationSigner(b'x'*32)
        token=signer.issue({'revision':'a'*64},now=100)
        self.assertEqual(signer.verify(token,{'revision':'a'*64},now=101),{'revision':'a'*64})
        for scope,now,candidate in [({'revision':'b'*64},101,token),({'revision':'a'*64},701,token),
                                    ({'revision':'a'*64},101,token[:-2]+'xx')]:
            with self.assertRaises(ValueError):signer.verify(candidate,scope,now=now)

    def test_claim_skip_locked_owner_and_expired_lease(self):
        first=self.repo.enqueue('VALIDATE',str(uuid4()),'a'*64);self.c.commit()
        with psycopg.connect(os.environ['AAT_FOUNDATION_TEST_DSN']) as other:
            self.c.execute('SELECT id FROM operations WHERE id=%s FOR UPDATE',(first['id'],))
            self.assertIsNone(self.module.Operations(other).claim('other',ttl=1,kinds=['VALIDATE']))
        self.c.rollback();claimed=self.repo.claim('owner',ttl=1,kinds=['VALIDATE']);self.c.commit()
        self.assertEqual(claimed['id'],first['id'])
        self.c.execute("UPDATE operations SET lease_until=now()-interval '1 second' WHERE id=%s",(first['id'],));self.c.commit()
        self.assertIsNone(self.repo.claim('new-owner',ttl=10,kinds=['VALIDATE']));self.c.commit()
        self.assertEqual(self.c.execute('SELECT state FROM operations WHERE id=%s',(first['id'],)).fetchone()[0],'NEEDS_RECONCILIATION')
