"""T140: canonical Compose startup on a new owned namespace, no .env setup.

Run on the host with AAT_RUN_FRESH_STARTUP=1 after local image policy passes.
Build preparation verifies canonical tags before any service starts; the
acceptance command itself remains `podman compose up --build -d`.
"""
import hashlib
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import time
import unittest
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[2]


class OneCommandStartupTests(unittest.TestCase):
    def test_fresh_start_restart_and_lost_secret_fail_closed(self):
        if os.environ.get('AAT_RUN_FRESH_STARTUP')!='1':
            raise RuntimeError('Explicit owned fresh-start fixture required: AAT_RUN_FRESH_STARTUP=1')
        if (ROOT/'.env').exists():raise RuntimeError('The default startup selector requires no .env file')
        phase_only=os.environ.get('AAT_T140_PHASE_ONLY')
        if phase_only is not None and phase_only not in ('EXTRACTION','COMMIT','FULL_REFRESH'):
            raise RuntimeError('AAT_T140_PHASE_ONLY must name one supported restart phase')
        project='aat-t140-'+secrets.token_hex(4)
        evidence=ROOT/'docs/testing/resume-20261112'/project
        evidence.mkdir(parents=True)
        environment=dict(os.environ,COMPOSE_PROJECT_NAME=project,
            PODMAN_COMPOSE_PROVIDER=str(ROOT/'.tools/docker-compose-5.6.0.exe'),
            AAT_FRONTEND_PORT='23001',AAT_BACKEND_PORT='28001',AAT_AIRFLOW_PORT='28081')
        for port in (23001,28001,28081):
            with socket.socket() as listener:listener.bind(('127.0.0.1',port))
        result={'status':'NOT_RUN','project':project,'existing_services_modified':False,
                'canonical_startup':['podman','compose','up','--build','-d'],
                'phase_only_diagnostic':phase_only}
        base=['podman','compose']
        started=False
        def run(command,timeout=300):
            return subprocess.run(command,cwd=ROOT,env=environment,capture_output=True,text=True,encoding='utf-8',timeout=timeout)
        def checked(command,label,timeout=300):
            process=run(command,timeout)
            # No command prints credentials; service logs are deliberately not collected.
            (evidence/(label+'.log')).write_text(process.stdout+process.stderr,encoding='utf-8')
            self.assertEqual(process.returncode,0,label+' failed; inspect owned evidence')
            return process.stdout
        def ready():
            deadline=time.monotonic()+240
            while time.monotonic()<deadline:
                try:
                    with urlopen('http://127.0.0.1:28001/api/v1/health/ready',timeout=5) as response:
                        if response.status==200 and json.load(response)['status']=='READY':return
                except (OSError,ValueError):pass
                time.sleep(2)
            self.fail('Owned fresh stack did not become READY')
        def public_snapshot():
            with urlopen('http://127.0.0.1:28001/api/v1/connections',timeout=10) as response:
                connections=json.load(response)
            with urlopen('http://127.0.0.1:28001/api/v1/templates/etl-definition',timeout=10) as response:
                template=hashlib.sha256(response.read()).hexdigest()
            return {'connections':sorted((r['id'],r['code']) for r in connections['items']),'template_sha256':template}
        try:
            preflight=checked(['python','-X','utf8','tests/tools/run_regression.py','--group','e2e','--preflight-only',
                     '--evidence-dir',str((evidence/'policy-preflight').relative_to(ROOT))],'policy-preflight')
            self.assertIn('PREFLIGHT_PASS',preflight,'Exact-image policy gate must pass before any service starts')
            # Prepare cache/tags and verify resulting exact IDs before runtime admission.
            checked([*base,'build'],'build-preparation',1800)
            images=json.loads((ROOT/'.tools/local-images.json').read_text())
            mapping={'localhost/aat-backend:0.1.0':'backend','localhost/aat-airflow:0.1.0':'airflow',
                     'localhost/aat-frontend:0.1.0':'frontend','localhost/aat-postgres:17.11':'postgres',
                     'localhost/aat-mysql:8.4.13':'mysql'}
            resolved=dict(images)
            for tag,kind in mapping.items():
                actual=run(['podman','image','inspect',tag,'--format','{{.Id}}'])
                self.assertEqual(actual.returncode,0)
                resolved[kind]=actual.stdout.strip()
            resolved['workbook_deps']=resolved['backend']
            images_path=ROOT/'.tools/local-images.json'
            if resolved!=images:
                # Canonical builds may produce different immutable IDs. Scan
                # their actual bytes instead of admitting unreviewed runtime or
                # rewriting the existing demo's manifest.
                prior=json.loads((ROOT/'.tools/local-images-provenance.json').read_text())
                prior_manifest=ROOT/prior['manifest']
                candidate_dir=evidence/'canonical-candidate'
                candidate_dir.mkdir()
                aliases={'tests':'backend-tests','e2e':'e2e-tests'}
                rows=[{'name':aliases.get(kind,kind),'image_id':identity,'ref':identity,
                       'build':'CANONICAL_BUILD' if kind in mapping.values() else 'REUSED_REVIEWED_ARTIFACT'}
                      for kind,identity in resolved.items() if kind!='workbook_deps']
                manifest=candidate_dir/'candidate-images.json'
                manifest.write_text(json.dumps({'phase':'t140','run_id':project[-8:],
                    'source_context':'.','captured_at':datetime.now(timezone.utc).isoformat(),
                    'images':rows,'build_command':['podman','compose','build'],
                    'source_revision':run(['git','rev-parse','HEAD']).stdout.strip()},indent=2)+'\n')
                snapshot={}
                excluded={'node_modules','dist','build','__pycache__','.pytest_cache','test-results','playwright-report'}
                for folder in ('backend','frontend','packages','etl_engine','airflow','docker','tests','samples','templates','specs'):
                    for path in (ROOT/folder).rglob('*'):
                        if path.is_file() and not any(p in excluded or p.endswith('.egg-info') for p in path.parts):
                            snapshot[path.relative_to(ROOT).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
                for name in ('docker-compose.yml','.dockerignore','.gitattributes','.env.example'):
                    snapshot[name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                (candidate_dir/'source-sha256.json').write_text(json.dumps(snapshot,indent=2)+'\n')
                previous_scan=prior_manifest.parent/'candidate-security.json'
                cache=json.loads(previous_scan.read_text())['cache_volume']
                checked(['python','-X','utf8','tests/tools/scan_portable_images.py','--manifest',str(manifest.relative_to(ROOT)),
                         '--reuse-scan',str(previous_scan.relative_to(ROOT)),'--cache-volume',cache],'canonical-policy-scan',1800)
                images_path=ROOT/'.tools'/(project+'-images.json')
                images_path.write_text(json.dumps(resolved,indent=2)+'\n')
                images_path.with_name(images_path.stem+'-provenance.json').write_text(json.dumps({
                    'manifest':str(manifest.relative_to(ROOT)),'source_sha256':str((candidate_dir/'source-sha256.json').relative_to(ROOT))},indent=2)+'\n')
                result['canonical_policy_manifest']=str(manifest.relative_to(ROOT))
            started=True
            began=time.monotonic()
            checked(result['canonical_startup'],'canonical-startup',1800)
            ready()
            result['startup_seconds']=round(time.monotonic()-began,3)
            baseline=public_snapshot()
            self.assertTrue({'pg_etl','mysql_etl'}<={code for _,code in baseline['connections']})
            from tests.tools.verify_running_workflow import verify
            if phase_only is None:
                workflow=verify(project,'http://localhost:23001','http://localhost:28081',evidence/'full-workflow',images_path)
                self.assertEqual(workflow['status'],'PASS')
            restart_runs={}
            phases=(phase_only,) if phase_only else ('EXTRACTION','COMMIT','FULL_REFRESH')
            for phase in phases:
                phase_result=verify(project,'http://localhost:23001','http://localhost:28081',
                    evidence/('restart-'+phase.lower()),images_path,restart_phase=phase)
                self.assertEqual(phase_result['status'],'PASS',phase+' phase restart failed')
                self.assertEqual(len(phase_result['phase_restart_checks']),1)
                restart_runs[phase]=phase_result['phase_restart_checks'][0]
            result['phase_restart_runs']=restart_runs
            if phase_only:
                result.update(status='DIAGNOSTIC_PASS',t140_acceptance=False)
                return
            baseline=public_snapshot()
            backend=checked([*base,'ps','-q','backend'],'backend-id').strip()
            api=checked([*base,'ps','-q','airflow-apiserver'],'airflow-id').strip()
            # Authentication must remain enabled for the actual Airflow API.
            auth=run(['podman','exec',api,'python','-c',
                "import urllib.request,urllib.error;\ntry: urllib.request.urlopen('http://127.0.0.1:8080/api/v2/dags'); print(200)\nexcept urllib.error.HTTPError as e: print(e.code)"])
            self.assertEqual(auth.returncode,0)
            self.assertIn(auth.stdout.strip(),('401','403'))
            checked([*base,'restart'],'restart',300)
            ready()
            self.assertEqual(public_snapshot(),baseline,'Restart must preserve seeded identities and template bytes')
            # Only rename a known synthetic fixture credential; always restore it.
            for label,selection in (
                ('secret',"p=Path('/secrets/backend_secrets/pg_etl')"),
                ('key',"import json;r=Path('/secrets/app_keyring');p=r/(json.loads((r/'current.json').read_text())['key_id']+'.key')")):
                hidden='from pathlib import Path;'+selection+";p.rename(p.with_name(p.name+'.t140-backup'))"
                restored='from pathlib import Path;'+selection+";p.with_name(p.name+'.t140-backup').rename(p)"
                helper=[*base,'run','--rm','--no-deps','--entrypoint','python','secrets-init','-c']
                checked([*helper,hidden],'hide-owned-'+label)
                try:
                    rejected=run([*base,'run','--rm','--no-deps','secrets-init'])
                    self.assertNotEqual(rejected.returncode,0,'Missing persistent '+label+' must block init')
                    result['missing_'+label+'_init_exit_code']=rejected.returncode
                finally:checked([*helper,restored],'restore-owned-'+label)
            empty_keyring=project+'-missing-keyring'
            checked(['podman','volume','create',empty_keyring],'empty-owned-keyring')
            try:
                rejected=run([*base,'run','--rm','--no-deps','-v',empty_keyring+':/secrets/app_keyring','secrets-init'])
                self.assertNotEqual(rejected.returncode,0,'Missing keyring volume must block init without replacing original secrets')
                result['missing_keyring_volume_exit_code']=rejected.returncode
            finally:checked(['podman','volume','rm',empty_keyring],'remove-empty-owned-keyring')
            ready()
            self.assertEqual(public_snapshot(),baseline,'Rejected init must not reset metadata')
            result.update(status='PASS',snapshot=baseline,airflow_unauthenticated_status=int(auth.stdout.strip()))
        except Exception:
            result['status']='FAIL'
            raise
        finally:
            if started:
                cleanup=run([*base,'down','--volumes'],300)
                result['cleanup_exit_code']=cleanup.returncode
                if cleanup.returncode:result['status']='CLEANUP_FAILED'
            (evidence/'result.json').write_text(json.dumps(result,indent=2)+'\n')
            print('FRESH_STARTUP_EVIDENCE '+str(evidence.relative_to(ROOT)),flush=True)
            if started:self.assertEqual(result['cleanup_exit_code'],0,'Owned fixture cleanup failed')
