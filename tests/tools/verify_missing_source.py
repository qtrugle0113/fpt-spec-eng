"""Exercise unavailable-source guards through an installed fixture's public API."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from uuid import UUID, uuid4
import httpx
from sqlalchemy import text
from aat_api.services.connections.service import transaction
from aat_api.services import files

references=json.loads(Path('/tmp/full-workflows.json').read_text())
if len(references)!=2:raise RuntimeError('Two owned UI fixture references required')
with httpx.Client(base_url='http://127.0.0.1:8000/api/v1',trust_env=False,timeout=30) as client:
    for item in references:
        if not re.fullmatch(r'full_(desktop|mobile)_[0-9]+',item['table']):raise RuntimeError('Invalid owned fixture')
        with transaction() as session:
            file=files.require(session,UUID(item['file']))
            if file.sha256!=item['checksum']:raise RuntimeError('Owned source checksum differs')
            path=files.source_path(file.safe_storage_key)
            upload=session.scalar(text('SELECT r.upload_id FROM etl_definition_revisions r JOIN etl_definitions d ON d.current_revision_id=r.id WHERE d.dag_id=:dag'),{'dag':item['dag']})
            intents=session.scalar(text('SELECT count(*) FROM run_intents WHERE dag_id=:dag'),{'dag':item['dag']})
        url='/definition-uploads/'+str(upload)+'/etl-preview'
        before=client.get(url)
        if before.status_code!=200:raise RuntimeError('Owned preview is not ready')
        preview=before.json()
        revision=next(row['id'] for row in preview['items'] if row['config']['dag_id']==item['dag'])
        if path.is_symlink():raise RuntimeError('Owned source must not be a symlink')
        mode=stat.S_IMODE(path.stat().st_mode)
        content=path.read_bytes()
        if hashlib.sha256(content).hexdigest()!=item['checksum']:raise RuntimeError('Owned file bytes differ')
        path.unlink()
        try:
            for response in (client.get(url),client.post('/dags/'+item['dag']+'/trigger',
                    headers={'Idempotency-Key':str(uuid4())},json={'expected_revision':revision,'confirmation_token':preview['confirmation_token']})):
                if response.status_code!=409 or response.json()['error']['code']!='FILE_SOURCE_UNAVAILABLE':
                    raise RuntimeError('Unavailable source was not safely rejected')
                if str(path) in response.text:raise RuntimeError('Storage path exposed')
            with transaction() as session:
                after=session.scalar(text('SELECT count(*) FROM run_intents WHERE dag_id=:dag'),{'dag':item['dag']})
                if after!=intents:raise RuntimeError('Rejected request created a run intent')
        finally:
            descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,mode)
            with os.fdopen(descriptor,'wb') as restored:restored.write(content)
        if client.get(url).status_code!=200:raise RuntimeError('Restored immutable source did not recover')
        print('MISSING_SOURCE_INSTALLED_VERIFIED '+json.dumps({'dag':item['dag'],'preview_status':409,'trigger_status':409,'new_intents':0,'restored_preview':200}))
