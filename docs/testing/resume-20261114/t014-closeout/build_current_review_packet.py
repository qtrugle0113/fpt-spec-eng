import json, hashlib
from pathlib import Path
root=Path.cwd(); out=root/'docs/testing/resume-20261114/t014-closeout'
old=root/'docs/testing/resume-20261114/full-baseline-final'
baseline=json.loads((old/'candidate-security.json').read_text())
current={'airflow':(out/'dnspython/security.json',out/'dnspython/raw-airflow.json'), 'airflow-security-stage':(out/'remediated-stage-security.json',out/'remediated-stage-raw.json')}
groups={}; targets=[]
for previous in baseline['images']:
    name=previous['name']
    if name in current:
        summary_path,raw_path=current[name]; summary=json.loads(summary_path.read_text()); row=summary['images'][0]
    else:
        summary_path=old/'candidate-security.json'; raw_path=old/'raw-reports'/(name+'.json'); summary=baseline; row=previous
    raw=json.loads(raw_path.read_text()); assert raw['Metadata']['ImageID'].removeprefix('sha256:')==row['image_id'].removeprefix('sha256:')
    findings=[(r,v) for r in raw.get('Results',[]) for v in r.get('Vulnerabilities',[]) if v['Severity'] in ('HIGH','CRITICAL')]
    assert len(findings)==len(row['high_critical'])
    targets.append({'name':name,'image_id':row['image_id'],'scan_date':summary['captured_at'],'scanner_db':summary['scanner_version_db'],'raw_path':raw_path.relative_to(root).as_posix(),'raw_sha256':hashlib.sha256(raw_path.read_bytes()).hexdigest(),'reused_unchanged_image':name not in current,'occurrences':len(findings)})
    for r,v in findings:
        key=(v['VulnerabilityID'],v['PkgName'],v['InstalledVersion'],v.get('FixedVersion') or '',v['Severity'])
        item=groups.setdefault(key,dict(advisory=key[0],package=key[1],version=key[2],fixed=key[3] or None,severity=key[4],impact_from_scanner=v.get('Title'),reference_from_scanner=v.get('PrimaryURL'),disposition='PENDING_REMEDIATION_OR_AUTHORIZED_REVIEW',contexts=[]))
        item['contexts'].append(dict(target=name,image=row['image_id'],package_target=r.get('Target'),package_type=r.get('Type'),package_path=v.get('PkgPath'),layer=v.get('Layer'),exposure='Runtime candidate' if name=='airflow' else 'Inspect target role and reachability; no automatic not-affected decision'))
result={'status':'BLOCKED','scope':'21 targets: rescan changed Airflow runtime and OS-patched stage; reuse 19 unchanged immutable artifacts with original reports and per-target DB provenance. Not one DB snapshot.','occurrences':sum(t['occurrences'] for t in targets),'groups':list(groups.values()),'group_count':len(groups),'targets':targets,'groups_without_fixed_version':sum(not k[3] for k in groups)}
(out/'current-review-packet.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print({k:v for k,v in result.items() if k not in ('groups','targets')})
