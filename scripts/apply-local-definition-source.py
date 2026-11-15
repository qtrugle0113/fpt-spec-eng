"""Nạp source Definition hiện tại cho backend demo local, giữ image và volume dữ liệu."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time
import uuid
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]


def run(*args):
    result=subprocess.run(['podman',*map(str,args)],capture_output=True,text=True,encoding='utf-8',timeout=180)
    if result.returncode: raise RuntimeError('Local source operation failed: '+str(args[0])+'; values suppressed')
    return result.stdout.strip()


def main():
    record=json.loads((ROOT/'.tools/local-demo.json').read_text(encoding='utf-8-sig'))
    project=record['project']
    if not project.startswith('aat-portable-demo-') or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in project):raise ValueError('Expected owned local demo')
    config_path=Path(record['compose_config']).resolve()
    if not config_path.is_relative_to(ROOT/'.tools'):raise ValueError('Invalid local config')
    config=json.loads(config_path.read_text(encoding='utf-8-sig'))
    state=json.loads(run('inspect',project+'-backend-1'))[0]
    if config.get('name')!=project or state['Config']['Labels'].get('com.docker.compose.project')!=project:raise ValueError('Local project mismatch')
    if any(v.get('target')=='/current' for name in ('backend','backend-worker') for v in config['services'][name].get('volumes',[])):raise ValueError('Existing source overlay requires manual review')
    bindings=state['HostConfig']['PortBindings']['8000/tcp']
    if not bindings or any(b['HostIp']!='127.0.0.1' for b in bindings):raise ValueError('Backend must be local loopback')
    origin='http://127.0.0.1:'+bindings[0]['HostPort']
    spec=importlib.util.spec_from_file_location('migration',ROOT/'scripts/configure-local-airflow-admin.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    before=module.snapshot(origin)
    suffix=uuid.uuid4().hex[:8]
    volume=project+'_definition_source_'+suffix
    loader=project+'-definition-source-'+suffix
    backup=ROOT/'.tools'/('compose-definition-before-'+suffix+'.json')
    backup.write_bytes(config_path.read_bytes())
    run('volume','create',volume)
    run('create','--name',loader,'--network=none','--user=0:0','-v',volume+':/current','--entrypoint=python',state['Image'],'-c',"from pathlib import Path;[p.chmod(0o755 if p.is_dir() else 0o644) for p in Path('/current').rglob('*')];print('Source snapshot ready')")
    try:
        for folder in ('backend','packages','etl_engine','docker','airflow','templates','samples'):
            run('cp',ROOT/folder,loader+':/current/'+folder)
        run('start','-a',loader)
    finally:run('rm',loader)
    key='definition_current_source'
    config['volumes'][key]={'name':volume}
    for name in ('backend','backend-worker'):
        service=config['services'][name]
        service.setdefault('volumes',[]).append({'type':'volume','source':key,'target':'/current','read_only':True,'volume':{'nocopy':True}})
        service.setdefault('environment',{}).update(PYTHONPATH='/current/backend/src:/current/packages:/current/etl_engine/src:/current',AAT_ASSETS_ROOT='/current',PYTHONDONTWRITEBYTECODE='1')
    config_path.write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8')
    os.environ['PODMAN_COMPOSE_PROVIDER']=str(ROOT/'.tools/docker-compose-5.6.0.exe')
    run('compose','-f',config_path,'-p',project,'config','--quiet')
    run('compose','-f',config_path,'-p',project,'up','-d','--no-build','--no-deps','--force-recreate','backend')
    for attempt in range(60):
        try:
            after=module.snapshot(origin)
            if before!=after:raise ValueError('Existing data changed')
            break
        except Exception:
            if attempt==59:raise
            time.sleep(2)
    evidence={'status':'PASS','project':project,'execution_mode':'CURRENT_SOURCE_ON_EXISTING_DEPENDENCY_IMAGES',
              'source_volume':volume,'compose_backup':str(backup.relative_to(ROOT)),
              'data_ids_unchanged':before==after,'image_unchanged':state['Image']==json.loads(run('inspect',project+'-backend-1'))[0]['Image'],
              'before':before,'after':after}
    output=ROOT/'docs/testing/definition-admin-20261115/demo-source-overlay.json'
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    print(json.dumps({key:value for key,value in evidence.items() if key not in ('before','after')}))


if __name__=='__main__':main()
