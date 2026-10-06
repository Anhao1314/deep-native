import sys,pathlib,tempfile,json,subprocess
bench=pathlib.Path('outputs/deep-native/evals/benchmark-v1').resolve();sys.path.insert(0,str(bench))
import harness
from transport import Relay,provider_tokens
python=pathlib.Path('work/benchmark-env/bin/python').absolute()
endpoint,model,key=harness.secret_config(pathlib.Path.home()/'.claude/settings.json')
for arm in ['A','B']:
 relay=Relay(endpoint,key)
 base=pathlib.Path(tempfile.mkdtemp(prefix='dn-v4-toy-',dir='/private/tmp'));root=base/'workspace';root.mkdir();home=base/'home';(home/'.claude').mkdir(parents=True);tmp=base/'tmp';tmp.mkdir()
 (root/'hello.py').write_text('def greet(name):\n    return "hello"\n')
 (root/'test_hello.py').write_text('import unittest\nfrom hello import greet\nclass T(unittest.TestCase):\n def test_name(self): self.assertEqual(greet("Ada"),"Hello, Ada!")\n')
 for cmd in [['git','init','-q'],['git','config','user.name','Smoke'],['git','config','user.email','smoke@example.invalid'],['git','add','.'],['git','commit','-qm','Isolated toy preflight']]:harness.checked(cmd,root)
 artifact=pathlib.Path('work/v4-preflight-'+arm).resolve()
 try:
  if arm=='B':
   helper=bench.parent.parent/'skills/deep-native/scripts/deep_native.py'
   installation=harness.command([str(python),str(helper),'--project',str(root),'install','--hooks'],root)
   assert installation['exit_code']==0
  result,events=harness.live_session(root,home,tmp,python,relay,model,arm,'Fix greet(name) so it returns Hello, <name>! Tests are run with python3 -m unittest. Execute pwd in Bash and run the tests. End with STATUS: DONE or STATUS: BLOCKED.',artifact,180,24)
  calls=relay.close();harness.dump(artifact/'api_calls.json',calls)
  verification=harness.command([str(python),'-m','unittest'],root,env={'PATH':str(python.parent)+':/usr/bin:/bin','HOME':str(home),'PYTHONDONTWRITEBYTECODE':'1'})
  print(arm,'exit',result['exit_code'],'independent_tests',verification['exit_code'],'skill',harness.behavior(events)['skill_invoked'],'model',sorted({c['response_model'] for c in calls if c.get('response_model')}),'tokens_available',provider_tokens(calls) is not None,'workspace',root,flush=True)
  assert verification['exit_code']==0,(result['final_response'],verification)
  transcript=(artifact/'transcript.jsonl').read_text()
  assert not __import__('re').search(r'operation not permitted: .*claude-.*-cwd',transcript)
  behavior=harness.behavior(events)
  assert behavior['successful_verification'],behavior
  assert result['last_observed_verified_source_hash'],result
  blocks=[block for e in events for block in e.get('message',{}).get('content',[]) if isinstance(block,dict)]
  calls_by_id={block['id']:block for block in blocks if block.get('type')=='tool_use'}
  bash_results=[block for block in blocks if block.get('type')=='tool_result' and calls_by_id.get(block.get('tool_use_id'),{}).get('name')=='Bash']
  assert any(not block.get('is_error') for block in bash_results),bash_results
  harness.dump(artifact/'preflight_assertions.json',{'independent_test_pass':True,'native_cwd_write_denials':0,'observed_successful_verification':True,'actual_successful_bash_results':sum(not block.get('is_error') for block in bash_results),'per_run_claude_tmpdir':harness.agent_env(home,tmp,python,relay,model).get('CLAUDE_CODE_TMPDIR'),'excluded_from_formal_results':True})
  if arm=='B':assert harness.behavior(events)['skill_invoked']
 finally:relay.close()
