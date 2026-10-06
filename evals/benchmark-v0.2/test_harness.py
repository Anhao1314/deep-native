import json,subprocess,tempfile,unittest
from pathlib import Path
from harness import *
from runtime import receipt,checkpoint,verify_freeze
class HarnessTests(unittest.TestCase):
 def test_frozen_inputs(self):verify_freeze()
 def test_receipt_staleness_and_protection(self):
  task=next(t for t in TASKS if t['id']=='F1')
  with tempfile.TemporaryDirectory(prefix='dn2-test-',dir='/private/tmp') as td:
   root=Path(td).resolve()/'workspace';prepare(root,task);reference(root,task);expected=protected(root)
   self.assertEqual(launcher(root)['exit_code'],0);self.assertIsNotNone(receipt(root,1,expected))
   p=root/'src/cachetools/__init__.py';p.write_text(p.read_text()+'\n# relevant source edit\n');self.assertIsNone(receipt(root,1,expected))
 def test_checkpoint_requires_substance(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'.deep-native').mkdir();p=root/'.deep-native/state.json'
   p.write_text(json.dumps({'note':'done','next':'restore'}));self.assertIsNone(checkpoint(root,'C'))
 def test_treatment_install_and_real_check(self):
  for arm in ['B','C']:
   with self.subTest(arm=arm),tempfile.TemporaryDirectory(prefix='dn2-install-',dir='/private/tmp') as td:
    root=Path(td).resolve()/'workspace';task=TASKS[2];prepare(root,task);reference(root,task)
    helper=OUT/'treatments'/arm/'skills/deep-native/scripts/deep_native.py'
    self.assertEqual(cmd([PYTHON,helper,'--project',root,'install','--hooks'],root)['exit_code'],0)
    installed=root/'.claude/skills/deep-native/scripts/deep_native.py';self.assertTrue(installed.exists())
    home,tmp=setup_dirs(root.parent);env=env_for(root,home,tmp,PYTHON,sid='11111111-1111-4111-8111-111111111111');bootstrap_temp_dirs(root)
    profile=root.parent/'runtime.sb';profile.write_text(profile_for(root,home,PYTHON,12345));prefix=['sandbox-exec','-D','CLI_PID=0','-f',profile,PYTHON,installed,'--project',root]
    for args in [['configure','--name','tests','--','python3','run_checks.py'],['begin','--session',env['CLAUDE_SESSION_ID'],'--goal','offline fixture verification'],['verify','--timeout','60']]:
     result=cmd(prefix+args,root,env);self.assertEqual(result['exit_code'],0,result)
if __name__=='__main__':unittest.main(verbosity=2)
