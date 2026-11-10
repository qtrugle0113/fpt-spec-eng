"""T091: expired source bytes can be collected only after 30 days and no refs."""
from datetime import datetime,timedelta,timezone
import hashlib
from pathlib import Path
import tempfile
import unittest
from uuid import uuid4
from tests.integration import test_authorization_repository as fixtures


class SourceCleanupTests(unittest.TestCase):
    def run_case(self,referenced=False,recent=False):
        from aat_api.workers import recovery
        self.assertTrue(hasattr(recovery,'collect_expired_sources'),'T091 source cleanup missing')
        helper=fixtures.AuthorizationRepositoryTests();helper.setUpClass();helper.setUp()
        identity=uuid4();key=uuid4().hex;content=b'id\n1\n';stamp=datetime.now(timezone.utc)-timedelta(days=1 if recent else 31)
        with helper.connect() as c:
            helper.insert(c,'uploaded_files',id=identity,original_name='fixture.csv',safe_storage_key=key,sha256=hashlib.sha256(content).hexdigest(),bytes=len(content),extension='.csv',
                parser_revision=1,validation_status='VALID',created_at=stamp,updated_at=stamp,expires_at=datetime.now(timezone.utc)-timedelta(hours=1),
                encoding='utf-8',delimiter=',',header_present=True,quote_char='"',escape_char=None,null_token='\\N')
            helper.insert(c,'file_parser_revisions',id=uuid4(),file_id=identity,revision=1,encoding='utf-8',delimiter=',',header_present=True,quote_char='"',escape_char=None,null_token='\\N')
            if referenced:
                original=helper.insert
                def insert(c,table,**values):
                    if table=='etl_definition_revisions':values['config_json']={'source':{'file_id':str(identity)}}
                    original(c,table,**values)
                helper.insert=insert;helper.case(c)
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/key;path.write_bytes(content)
            recovery.collect_expired_sources(helper.connect,root=root)
            self.assertEqual(path.exists(),referenced or recent)
        with helper.connect() as c:
            row=c.execute('SELECT sha256,bytes FROM uploaded_files WHERE id=%s',(identity,)).fetchone()
            self.assertEqual(row,(hashlib.sha256(content).hexdigest(),len(content)))

    def test_unreferenced_source_expires_after_30_days(self):self.run_case()
    def test_referenced_source_is_kept_even_after_expiry(self):self.run_case(referenced=True)
    def test_shortened_expiry_cannot_bypass_30_day_source_retention(self):self.run_case(recent=True)
