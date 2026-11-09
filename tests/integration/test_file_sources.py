"""T062: real disk/metadata storage, exact upload bound and interrupted publication."""
import asyncio
import importlib
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from aat_metadata.models.definitions import UploadedFile
from aat_metadata.repositories.base import create_app_engine
from aat_api.errors import APIError
from tests.api.test_files import PARSER


class SyntheticStream:
    filename='same.csv'
    def __init__(self,size,interrupt=False):self.remaining=size;self.interrupt=interrupt;self.reads=0
    async def read(self,size=-1):
        if not 0<size<=65536:raise AssertionError('Upload attempted an unbounded read')
        self.reads+=1
        if self.interrupt and self.reads==2:raise OSError('Synthetic source interruption')
        count=min(size,self.remaining);self.remaining-=count
        return b'x'*count
    async def close(self):pass


class FileStorageTests(unittest.TestCase):
    def setUp(self):
        if os.environ.get('AAT_FOUNDATION_DISPOSABLE')!='1':raise RuntimeError('Disposable fixture required')
        try:self.service=importlib.import_module('aat_api.services.files')
        except ModuleNotFoundError as error:
            if error.name.startswith('aat_api.'):raise AssertionError('T064 immutable file storage is not implemented') from None
            raise
        self.engine=create_app_engine();self.addCleanup(self.engine.dispose)
        self.root=Path(os.environ['AAT_UPLOADS_ROOT'])

    def snapshot(self):
        with Session(self.engine) as session:count=session.scalar(select(func.count()).select_from(UploadedFile))
        return count,{path.relative_to(self.root) for path in self.root.rglob('*') if path.is_file()}

    def test_interrupted_upload_does_not_publish_or_leave_partial_content(self):
        before=self.snapshot()
        with self.assertRaises(APIError):asyncio.run(self.service.store(SyntheticStream(100000,interrupt=True),PARSER))
        self.assertEqual(self.snapshot(),before)

    def test_exact_256_mib_upload_bound_without_buffering_whole_source(self):
        before=self.snapshot();source=SyntheticStream(256*1024*1024+1)
        with self.assertRaises(APIError) as error:asyncio.run(self.service.store(source,PARSER))
        self.assertEqual(error.exception.status,413);self.assertEqual(source.remaining,0)
        self.assertEqual(self.snapshot(),before)

    def test_expired_file_referenced_by_definition_or_binding_is_not_collectable(self):
        from datetime import datetime,timezone,timedelta
        from uuid import UUID
        from tests.api import test_files
        file=asyncio.run(self.service.store(SyntheticStream(20),PARSER));file['id']=str(file['id'])
        identity=UUID(file['id'])
        with Session(self.engine) as session,session.begin():session.get(UploadedFile,identity).expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)
        self.assertTrue(self.service.can_collect(identity))
        test_files.FilesAPITests.dependency_fixture(self,file,active=True,uncertain=True)
        self.assertFalse(self.service.can_collect(identity))

    def test_durable_full_validation_checks_tail_checksum_and_missing_source(self):
        from uuid import UUID,uuid4
        from aat_api.schemas.definitions import ValidationRequest
        from aat_api.workers.files import request_validation,execute
        from aat_api.workers.main import connect
        from aat_api.services.operations import Operations
        class BytesSource(SyntheticStream):
            def __init__(self,data):self.data=data;self.position=0
            async def read(self,size):
                chunk=self.data[self.position:self.position+size];self.position+=len(chunk)
                return chunk
        cases=[('valid',b'a,b\n1,2\n','SUCCEEDED',None),
            ('tail',b'a,b\n'+b'1,2\n'*101+b'private-bad-row\n','FAILED','FIELD_COUNT_MISMATCH'),
            ('checksum',b'a,b\n1,2\n','FAILED','SOURCE_CHECKSUM_MISMATCH'),
            ('missing',b'a,b\n1,2\n','FAILED','FILE_SOURCE_UNAVAILABLE')]
        for name,data,expected_state,expected_code in cases:
            with self.subTest(case=name):
                file=asyncio.run(self.service.store(BytesSource(data),PARSER));identity=file['id']
                operation_id=request_validation(identity,ValidationRequest(expected_sha256=file['sha256'],parser_revision=1),uuid4())
                with Session(self.engine) as session:key=session.get(UploadedFile,identity).safe_storage_key
                path=self.service.source_path(key)
                if name=='missing':path.unlink()
                elif name=='checksum':path.write_bytes(b'a,b\n3,4\n')
                owner='t065-durable-fixture'
                with connect() as connection:operation=Operations(connection).claim(owner,ttl=300,kinds=['FILE_VALIDATE'])
                self.assertEqual(operation['id'],operation_id)
                state,code=execute(operation,owner)
                self.assertEqual((state,code),(expected_state,expected_code))
                with connect() as connection:Operations(connection).finish(operation_id,owner,state=state,error_code=code)
                detail=self.service.detail(identity)
                self.assertEqual(detail['validation_status'],'VALID' if name=='valid' else 'INVALID')

    def test_real_metadata_commit_with_lost_ack_preserves_complete_blob(self):
        from contextlib import contextmanager
        from sqlalchemy.exc import OperationalError
        import hashlib
        class AckLostSession(Session):
            @contextmanager
            def begin(self,**options):
                with super().begin(**options) as transaction:yield transaction
                raise OperationalError('COMMIT',None,ConnectionError('Synthetic lost acknowledgement after actual commit'))
        with Session(self.engine) as session:before=set(session.scalars(select(UploadedFile.id)))
        with patch.object(self.service,'Session',AckLostSession),self.assertRaises(APIError) as error:
            asyncio.run(self.service.store(SyntheticStream(20),PARSER))
        self.assertEqual(error.exception.code,'UPLOAD_PUBLICATION_UNCERTAIN')
        with Session(self.engine) as session:
            rows=list(session.scalars(select(UploadedFile).where(UploadedFile.id.not_in(before))))
            self.assertEqual(len(rows),1);file=rows[0]
            data=self.service.source_path(file.safe_storage_key).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(),file.sha256)
            self.assertEqual(len(data),file.bytes)

    def test_actual_http_disconnect_does_not_publish_source_and_server_remains_live(self):
        import json,socket,subprocess,sys,tempfile,time,urllib.request
        before=self.snapshot()
        with socket.socket() as reserved:reserved.bind(('127.0.0.1',0));port=reserved.getsockname()[1]
        with tempfile.TemporaryFile() as log:
            process=subprocess.Popen([sys.executable,'-m','uvicorn','aat_api.main:app','--host','127.0.0.1','--port',str(port),'--no-access-log','--log-level','error'],stdout=log,stderr=log)
            try:
                url='http://127.0.0.1:'+str(port)+'/api/v1/health/live'
                for _ in range(100):
                    try:
                        with urllib.request.urlopen(url,timeout=.2) as response:
                            if response.status==200:break
                    except OSError:time.sleep(.05)
                else:self.fail('Disposable HTTP server did not start')
                boundary='aat-interrupted-public-fixture'
                prefix=(f'--{boundary}\r\nContent-Disposition: form-data; name="parser_json"\r\n\r\n'+json.dumps(PARSER)+
                    f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="interrupted.csv"\r\nContent-Type: text/csv\r\n\r\n').encode()
                headers=(f'POST /api/v1/files HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nContent-Type: multipart/form-data; boundary={boundary}\r\nContent-Length: {64*1024*1024}\r\nConnection: close\r\n\r\n').encode()
                with socket.create_connection(('127.0.0.1',port),timeout=5) as client:
                    client.sendall(headers+prefix+b'x'*(2*1024*1024));client.shutdown(socket.SHUT_WR)
                for _ in range(20):
                    time.sleep(.05)
                    with urllib.request.urlopen(url,timeout=1) as response:self.assertEqual(response.status,200)
                self.assertEqual(self.snapshot(),before)
            finally:
                process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)

    def test_storage_key_collision_does_not_delete_another_partial_upload(self):
        from uuid import uuid4
        key=uuid4();path=self.root/(key.hex+'.part');path.write_bytes(b'existing upload in progress')
        try:
            with patch.object(self.service,'uuid4',side_effect=[key,uuid4()]),self.assertRaises(APIError):
                asyncio.run(self.service.store(SyntheticStream(20),PARSER))
            self.assertTrue(path.exists(),'Another upload partial was deleted')
            self.assertEqual(path.read_bytes(),b'existing upload in progress')
        finally:path.unlink(missing_ok=True)
