"""Frozen, sequential twelve-run mechanism ablation; no automatic retries."""
import argparse,hashlib,json,os,random,selectors,shutil,signal,subprocess,sys,tempfile,time,uuid
from pathlib import Path
from fixtures import TASKS,ARMS,UPSTREAM,BUDGET,manifest,seed,reference,visible_tests
from environment import env_for,profile_for,preflight,native_git
from isolation import ProcessOwner,bootstrap_temp_dirs
from transport import Relay,provider_tokens
HERE=Path(__file__).resolve().parent
REPO=HERE.parent.parent
WORK=REPO.parent.parent/'work'
PYTHON=WORK/'ablation-env/bin/python'
CACHE=WORK/'cachetools-v02'
OUT=HERE/'campaign'
GIT=str(native_git())
def dump(p,v):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def cmd(args,cwd=None,env=None,timeout=120):
 start=time.monotonic()
 try:
  p=subprocess.run(list(map(str,args)),cwd=cwd,env=env,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=timeout)
  return dict(exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr,duration_seconds=time.monotonic()-start)
 except subprocess.TimeoutExpired as e:return dict(exit_code=124,stdout=str(e.stdout or ''),stderr=str(e.stderr or ''),duration_seconds=time.monotonic()-start)
def git(root,*args):
 r=cmd([GIT,*args],root);assert r['exit_code']==0,r;return r['stdout'].strip()
def prepare(root,task):
 root.mkdir(parents=True)
 data=subprocess.run([GIT,'-C',str(CACHE),'archive',UPSTREAM['commit']],capture_output=True,check=True).stdout
 subprocess.run(['tar','-x','-C',str(root)],input=data,check=True)
 assert not any(root.rglob('CLAUDE.md')) and not any(root.rglob('AGENTS.md')) and not (root/'.claude').exists()
 seed(root,task,HERE)
 git(root,'init','-q');git(root,'config','user.name','Benchmark Fixture');git(root,'config','user.email','benchmark@example.invalid');git(root,'add','-A')
 env={**os.environ,'GIT_AUTHOR_DATE':'2026-10-06T00:00:00+0000','GIT_COMMITTER_DATE':'2026-10-06T00:00:00+0000'}
 assert cmd([GIT,'commit','-qm','Frozen fixture '+task['id']],root,env)['exit_code']==0
 (root/'.git/info/exclude').write_text('\n.claude/\n.deep-native/\n.deep-native.json\n.experiment/\n__pycache__/\n*.pyc\n.pytest_cache/\n')
 if task['id']=='E1':(root/'.fixture-readonly').chmod(0o555)
 return git(root,'rev-parse','HEAD')
def phase(root,task,n):
 (root/'benchmark_tests.py').write_text(visible_tests(HERE,task['id'],n));(root/'benchmark_phase.json').write_text(json.dumps({'task':task['id'],'phase':n})+'\n')
def fingerprint(root):
 files=sorted(list((root/'src/cachetools').rglob('*.py'))+list((root/'agent_tests').rglob('*.py'))+[root/'benchmark_tests.py',root/'benchmark_phase.json',root/'run_checks.py',root/'check_receipt.py'])
 return hashlib.sha256(b''.join(str(p.relative_to(root)).encode()+b'\0'+p.read_bytes()+b'\0' for p in files)).hexdigest()
def protected(root):
 return {str(p.relative_to(root)):sha(p) for p in sorted(list((root/'tests').rglob('*'))+[root/'benchmark_tests.py',root/'benchmark_phase.json',root/'check_receipt.py']) if p.is_file()}
def setup_dirs(base):
 home=base/'home';tmp=base/'tmp';(home/'.claude').mkdir(parents=True,exist_ok=True);tmp.mkdir(exist_ok=True);return home,tmp
def grade(root,task,n,commit):
 with tempfile.TemporaryDirectory(prefix='dn2-grade-',dir='/private/tmp') as td:
  base=Path(td).resolve();dest=base/'workspace';dest.mkdir();home,tmp=setup_dirs(base)
  data=subprocess.run([GIT,'-C',str(root),'archive',commit],capture_output=True,check=True).stdout
  subprocess.run(['tar','-x','-C',str(dest)],input=data,check=True)
  for name in task['files']:
   p=root/name
   if not p.is_file() or p.is_symlink():return {'pass':False,'reason':'missing_or_symlink','path':name}
   shutil.copyfile(p,dest/name)
  if (root/'agent_tests').exists():shutil.copytree(root/'agent_tests',dest/'agent_tests',symlinks=True)
  if any(p.is_symlink() for p in dest.rglob('*')):return {'pass':False,'reason':'symlink'}
  phase(dest,task,n);env=env_for(dest,home,tmp,PYTHON);bootstrap_temp_dirs(dest)
  profile=base/'grade.sb';profile.write_text(profile_for(dest,home,PYTHON,None,[HERE/'task_tests.py']))
  prefix=['sandbox-exec','-D','CLI_PID=0','-f',profile]
  contract=cmd(prefix+[PYTHON,HERE/'task_tests.py',task['id'],str(n)],dest,env)
  upstream=cmd(prefix+[PYTHON,'-m','pytest','-q','tests'],dest,env)
  extra=cmd(prefix+[PYTHON,'-m','pytest','-q','agent_tests'],dest,env) if (dest/'agent_tests').exists() else {'exit_code':0,'stdout':'No agent tests supplied','stderr':''}
  return {'pass':all(r['exit_code']==0 for r in [contract,upstream,extra]),'contract':contract,'upstream':upstream,'agent_tests':extra}
def launcher(root):
 base=root.parent;home,tmp=setup_dirs(base);env=env_for(root,home,tmp,PYTHON);bootstrap_temp_dirs(root)
 p=base/'launch.sb';p.write_text(profile_for(root,home,PYTHON,12345))
 return cmd(['sandbox-exec','-D','CLI_PID=0','-f',p,PYTHON,'run_checks.py'],root,env)
def cleanup_probe():
 p=subprocess.Popen([str(PYTHON),'-c','import subprocess,time;subprocess.Popen(["/bin/sleep","30"],start_new_session=True);time.sleep(2)'],start_new_session=True)
 owner=ProcessOwner(p)
 for _ in range(10):owner.update();time.sleep(.1)
 result=owner.cleanup();time.sleep(.2);result['remaining']=owner.update();result['passed']=not result['remaining'] and result['observed_descendants']>=1
 assert result['passed'],result
 return result
def freeze():
 assert not OUT.exists(),'Refusing to replace an existing freeze.'
 OUT.mkdir();preflight(PYTHON,OUT/'preflight.json');dump(OUT/'process-preflight.json',cleanup_probe())
 calibration={}
 for task in TASKS:
  with tempfile.TemporaryDirectory(prefix='dn2-cal-',dir='/private/tmp') as td:
   root=Path(td).resolve()/'workspace';commit=prepare(root,task)
   before=grade(root,task,1,commit);launch_before=launcher(root)
   reference(root,task,1 if task['id']=='R1' else 2)
   after1=grade(root,task,1,commit);launch_after=launcher(root)
   halfway=grade(root,task,2,commit) if task['id']=='R1' else None
   if task['id']=='R1':
    # Reset only the offline calibration fixture before full reference repair.
    original=subprocess.run([GIT,'show',commit+':src/cachetools/__init__.py'],cwd=root,capture_output=True,check=True).stdout
    (root/'src/cachetools/__init__.py').write_bytes(original);reference(root,task,2)
   phase(root,task,2);after2=grade(root,task,2,commit);launch_final=launcher(root)
   calibration[task['id']]={'fixture_commit':commit,'before':before,'launcher_before':launch_before,'reference_phase1':after1,'reference_launcher_phase1':launch_after,'halfway_full_grade':halfway,'reference_final':after2,'reference_launcher_final':launch_final}
   dump(OUT/'calibration.json',calibration)
   assert before['pass']==(task['id']=='E1'),task['id']
   assert launch_before['exit_code']!=0 and after1['pass'] and after2['pass'] and launch_after['exit_code']==0 and launch_final['exit_code']==0,task['id']
   if halfway:assert not halfway['pass']
   if task['id']=='E1':(root/'.fixture-readonly').chmod(0o755)
 for arm,commit in ARMS.items():
  if not commit:continue
  dest=OUT/'treatments'/arm;dest.mkdir(parents=True)
  data=subprocess.run([GIT,'archive',commit,'skills/deep-native'],cwd=REPO,capture_output=True,check=True).stdout
  subprocess.run(['tar','-x','-C',str(dest)],input=data,check=True)
 schedule=[];rng=random.Random(20261007)
 for task in TASKS:
  arms=list(ARMS);rng.shuffle(arms)
  for arm in arms:schedule.append({'run_id':f'{len(schedule)+1:02d}-{task["id"]}-{arm}','task_id':task['id'],'arm':arm})
 endpoint,model,_=config()
 audit={'claude':cmd(['claude','--version']),'claude_sha256':sha(Path(shutil.which('claude')).resolve()),'python':cmd([PYTHON,'--version']),'packages':cmd([PYTHON,'-m','pip','freeze']),'git':cmd([GIT,'--version']),'endpoint':endpoint,'model':model,'skill_candidate':ARMS['C'],'harness_parent_commit':git(REPO,'rev-parse','HEAD'),'created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'cost':'unavailable; never infer billed cost from CLI estimates'}
 dump(OUT/'audit.json',audit);dump(OUT/'manifest.json',manifest());dump(OUT/'schedule.json',schedule)
 files=list(HERE.glob('*.py'))+list((OUT/'treatments').rglob('*'))+[OUT/'audit.json',OUT/'manifest.json',OUT/'schedule.json',OUT/'calibration.json',OUT/'preflight.json',OUT/'process-preflight.json']
 dump(OUT/'freeze.json',{str(p.relative_to(HERE)):sha(p) for p in files if p.is_file()})
def config():
 data=json.loads((Path.home()/'.claude/settings.json').read_text());e=data.get('env',{});token=e.get('ANTHROPIC_AUTH_TOKEN') or e.get('ANTHROPIC_API_KEY');endpoint=e.get('ANTHROPIC_BASE_URL');model=e.get('ANTHROPIC_MODEL') or data.get('model')
 assert token and model and endpoint=='https://api.deepseek.com/anthropic';return endpoint,model,token
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('action',choices=['freeze']);args=parser.parse_args();freeze()
