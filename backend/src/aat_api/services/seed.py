"""Insert missing local samples without overwriting operator metadata or keys."""
import hashlib
import json
import os
from pathlib import Path
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from aat_metadata.models.connections import Connection,ConnectionRevision,ConnectionSecret
from aat_metadata.models.definitions import UploadedFile
from aat_metadata.models.file_parsers import FileParserRevision
from aat_metadata.models.settings import ApplicationSetting
from aat_metadata.secrets.codec import SecretCodec


def seed(connection,root):
    disposable=os.environ.get('AAT_FOUNDATION_DISPOSABLE')=='1'
    keyroot=Path(os.environ.get('AAT_APP_KEYRING','/secrets/app_keyring'))
    codec=SecretCodec(keyroot)
    session=Session(bind=connection,expire_on_commit=False)
    # Verify existing secrets before creating anything; never replace a lost key.
    for secret in session.scalars(select(ConnectionSecret)):
        codec.decrypt(secret.key_id,secret.ciphertext)
    defaults={'default_batch_size':1000,'dashboard_refresh_interval':30,'default_timezone':'UTC','staging_retention_days':7}
    for key,value in defaults.items():
        if session.get(ApplicationSetting,key) is None:
            session.add(ApplicationSetting(key=key,value_json=value,value_type='string' if isinstance(value,str) else 'integer'))
    secrets=Path(os.environ.get('AAT_BACKEND_SECRETS','/secrets/backend'))
    for code,typ,host,port,schema,secret_name in [('pg_etl','POSTGRESQL','postgres',5432,'public','pg_etl'),
                                                ('mysql_etl','MYSQL','mysql',3306,None,'mysql_etl')]:
        if session.scalar(select(Connection).where(Connection.normalized_code==code)) is not None:continue
        password='synthetic-fixture-password' if disposable else (secrets/secret_name).read_text()
        secret=ConnectionSecret.from_plaintext(codec,password);session.add(secret)
        parent=Connection(code=code,name=code,database_type=typ);session.add(parent);session.flush()
        revision=ConnectionRevision(connection_id=parent.id,revision=1,database_type=typ,host=host,port=port,
            database_name='etl_test',schema_name=schema,username='aat_etl',secret_id=secret.id)
        session.add(revision);session.flush();parent.current_revision_id=revision.id
    uploads=Path(os.environ.get('AAT_UPLOADS_ROOT','/data/uploads'));uploads.mkdir(parents=True,exist_ok=True,mode=0o750)
    manifest=json.loads((root/'specs/001-airflow-automation-tool/contracts/design-validation.json').read_text(encoding='utf-8'))
    for number,extension,delimiter in [(1,'.csv',','),(2,'.txt','|')]:
        file_id=UUID('11111111-1111-4111-8111-111111111111' if number==1 else '22222222-2222-4222-8222-222222222222')
        if session.get(UploadedFile,file_id) is not None:continue
        source=root/'samples/data'/('customers'+extension);data=source.read_bytes()
        # Validate actual published bytes, never normalize uploads/fixtures here.
        if b'\r' in data:raise RuntimeError('Sample checkout must preserve LF bytes')
        expected=next(row for row in manifest['sample_datasets'] if row['seed_file_id']==str(file_id))
        if hashlib.sha256(data).hexdigest()!=expected['sha256'] or delimiter!=expected['delimiter']:
            raise RuntimeError('Sample manifest identity mismatch')
        target=uploads/file_id.hex
        if target.exists():
            if target.read_bytes()!=data:raise RuntimeError('Existing sample storage identity differs')
        else:
            with target.open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
            target.chmod(0o640)
            if not disposable:os.chown(target,50000,50000)
        file=UploadedFile(id=file_id,original_name=source.name,safe_storage_key=file_id.hex,
            sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),extension=extension,encoding='utf-8',
            delimiter=delimiter,header_present=True,quote_char='"',escape_char=None,null_token='\\N',validation_status='PENDING')
        session.add(file);session.flush()
        session.add(FileParserRevision(file_id=file.id,revision=1,encoding=file.encoding,delimiter=file.delimiter,
            header_present=file.header_present,quote_char=file.quote_char,escape_char=file.escape_char,null_token=file.null_token))
    session.flush();session.close()
