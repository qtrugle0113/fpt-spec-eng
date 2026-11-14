"""Chạy compatibility tests thật trên immutable images đã được duyệt."""
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tests.integration.test_image_compatibility import ImageCompatibilityTests

def main():
    images=json.loads((ROOT/'.tools/accepted-images.json').read_text())
    mapping={'localhost/aat-backend:0.1.0':images['backend'],
             'localhost/aat-airflow:0.1.0':images['airflow'],
             'localhost/aat-e2e:0.1.0':images['e2e']}
    original=ImageCompatibilityTests.run_image
    commands=[]
    def pinned(self,*args,code=None):
        args=tuple(mapping.get(arg,arg) for arg in args)
        commands.append(list(args))
        return original(self,*args,code=code)
    ImageCompatibilityTests.run_image=pinned
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(ImageCompatibilityTests)
    out=ROOT/'docs/testing/resume-20261114/accepted-handover';out.mkdir(parents=True,exist_ok=True)
    with (out/'compatibility.txt').open('w',encoding='utf8') as log:
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    data={'status':'PASS' if result.wasSuccessful() else 'FAIL','tests':result.testsRun,
          'images':images,'commands':commands,'mapping_only':True,'assertions_unchanged':True}
    (out/'compatibility.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf8')
    print(data['status'],result.testsRun)
    return 0 if result.wasSuccessful() else 1

if __name__=='__main__':raise SystemExit(main())
