"""Build current frontend source using an existing pinned offline toolchain."""
import argparse
import hashlib
import json
from pathlib import Path
import secrets
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--image',required=True)
parser.add_argument('--evidence-dir',required=True)
args=parser.parse_args()
evidence=(ROOT/args.evidence_dir).resolve()
if not evidence.is_relative_to(ROOT):parser.error('Evidence must stay in workspace')
evidence.mkdir(parents=True,exist_ok=True)
name='aat-frontend-source-'+secrets.token_hex(4)
artifact=ROOT/'.tools'/name
result={'published_ports':False,'network':'none','existing_services_modified':False,'status':'NOT_RUN'}


def run(*command,check=True):
    process=subprocess.run(['podman',*command],capture_output=True,text=True,encoding='utf-8',timeout=180)
    if check and process.returncode:raise RuntimeError('Frontend source command failed: '+command[0])
    return process


try:
    result['image_id']=run('image','inspect',args.image,'--format','{{.Id}}').stdout.strip()
    # Match Dockerfile COPY inputs and avoid Tailwind scanning stale source or
    # host-only scripts from an earlier toolchain image's /app directory.
    build_root='/tmp/aat-frontend'
    script="const fs=require('node:fs');const cp=require('node:child_process');const npm=require('/usr/local/lib/node_modules/npm/package.json').version;if(process.version!=='v22.23.4'||npm!=='12.2.2')throw Error('Toolchain baseline mismatch');fs.symlinkSync('/app/node_modules','node_modules');console.log(JSON.stringify({node:process.version,npm}));cp.execFileSync('npm',['run','build'],{stdio:'inherit'});"
    run('create','--name',name,'--network','none','--memory','512m','--workdir',build_root,'--entrypoint','node',args.image,'-e',script)
    lock=evidence/'toolchain-package-lock.json'
    run('cp',name+':/app/package-lock.json',str(lock))
    if lock.read_bytes()!=(ROOT/'frontend/package-lock.json').read_bytes():
        raise RuntimeError('Existing node_modules toolchain has a different dependency lock')
    context=ROOT/'.tools'/(name+'-context');context.mkdir()
    for entry in ('package.json','package-lock.json','index.html','tsconfig.json','vite.config.ts','src'):
        source=ROOT/'frontend'/entry
        if source.is_dir():shutil.copytree(source,context/entry)
        else:shutil.copy2(source,context/entry)
    run('cp',str(context),name+':'+build_root)
    snapshot={path.relative_to(ROOT/'frontend').as_posix():hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (ROOT/'frontend').rglob('*') if path.is_file() and not any(part in path.parts for part in ('node_modules','dist','__pycache__'))}
    (evidence/'source-sha256.json').write_text(json.dumps(snapshot,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    process=run('start','-a',name,check=False)
    (evidence/'build.log').write_text(process.stdout+process.stderr,encoding='utf-8')
    result['exit_code']=int(run('inspect',name,'--format','{{.State.ExitCode}}').stdout.strip())
    result['oom_killed']=run('inspect',name,'--format','{{.State.OOMKilled}}').stdout.strip()=='true'
    result['status']='PASS' if result['exit_code']==0 else 'FAIL'
    if result['exit_code']==0:
        artifact.mkdir(parents=True)
        run('cp',name+':'+build_root+'/dist/.',str(artifact))
        result['artifact_dir']=str(artifact.relative_to(ROOT))
    print((process.stdout+process.stderr)[-4500:])
finally:
    result['cleanup_exit_code']=run('rm','-f',name,check=False).returncode
    (evidence/'frontend-source-results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
if result.get('exit_code',1):raise SystemExit(1)
