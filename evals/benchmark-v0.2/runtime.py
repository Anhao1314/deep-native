"""Real Claude Code execution. All interruptions require completed functional evidence."""
from harness import *

def receipt(root,n,expected):
 p=root/'.experiment/checks.jsonl'
 if not p.exists() or protected(root)!=expected:return None
 try:rows=[json.loads(x) for x in p.read_text().splitlines()]
 except (ValueError,OSError):return None
 return next((r for r in reversed(rows) if r.get('passed') and r.get('phase')==n and r.get('source_before')==r.get('source_after')==fingerprint(root)),None)
def checkpoint(root,arm):
 if arm=='A':
  p=root/'PROGRESS.md';note=p.read_text() if p.is_file() else '';value={'note':note,'next':note}
 else:
  p=root/'.deep-native/state.json'
  try:value=json.loads(p.read_text())
  except (OSError,ValueError):return None
 note=value.get('note','');nxt=value.get('next','')
 # Qualification is based on real milestones plus substantive retained task facts.
 if len(note)<60 or len(nxt)<12 or 'snapshot' not in note.lower() or 'restore' not in (note+' '+nxt).lower():return None
 return value

def live(root,task,arm,home,tmp,relay,model,artifact,seconds,turns,commit,expected,n=1,resume=None):
 sid=resume or str(uuid.uuid4());prompt=task['prompt'] if n==1 else task['continuation']
 argv=['claude','-p',prompt,'--model',model,'--effort','max','--setting-sources','project,local','--strict-mcp-config','--mcp-config','{"mcpServers":{}}','--tools','Bash,Read,Edit,Write,Glob,Grep,Skill','--allowedTools','Bash,Read,Edit,Write,Glob,Grep,Skill','--permission-mode','dontAsk','--output-format','stream-json','--verbose','--include-hook-events','--max-turns',str(turns)]
 argv+=['--resume',sid] if resume else ['--session-id',sid]
 if arm!='A':argv+=['--append-system-prompt',manifest()['activation']]
 env=env_for(root,home,tmp,PYTHON,relay.url,model,sid);bootstrap_temp_dirs(root)
 profile=root.parent/'sandbox.sb';profile.write_text(profile_for(root,home,PYTHON,relay.server.server_port))
 argv=['/bin/sh','-c','profile=$1; shift; exec sandbox-exec -D "CLI_PID=$$" -f "$profile" "$@"','benchmark-launcher',str(profile)]+argv
 artifact.mkdir(parents=True);dump(artifact/'command.json',argv);dump(artifact/'environment.json',env);(artifact/'prompt.txt').write_text(prompt);shutil.copyfile(profile,artifact/'sandbox.sb')
 events=[];tools={};observations=[];buffer=b'';reason=None;qualified=None;started=time.monotonic();seen_receipts=set()
 with (artifact/'transcript.jsonl').open('w') as log,(artifact/'stderr.txt').open('w') as err:
  proc=subprocess.Popen(argv,cwd=root,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=err,start_new_session=True)
  owner=ProcessOwner(proc);selector=selectors.DefaultSelector();selector.register(proc.stdout,selectors.EVENT_READ)
  try:
   while True:
    owner.update()
    if time.monotonic()-started>=seconds:reason='wall_budget';break
    for key,_ in selector.select(.15):
     data=os.read(key.fileobj.fileno(),65536)
     if not data:selector.unregister(key.fileobj);continue
     buffer+=data
     while b'\n' in buffer:
      line,buffer=buffer.split(b'\n',1);log.write(line.decode('utf8','replace')+'\n');log.flush()
      try:e=json.loads(line)
      except ValueError:continue
      events.append(e)
      for c in e.get('message',{}).get('content',[]):
       if not isinstance(c,dict):continue
       if c.get('type')=='tool_use':
        tools[c['id']]=c; c['_observed_epoch']=time.time()
       if c.get('type')=='tool_result':
        tool=tools.get(c.get('tool_use_id'),{});r=receipt(root,n,expected)
        content=json.dumps(c,ensure_ascii=False)
        # A receipt only qualifies when the completed tool output corroborates it.
        native_proof=False
        if r and tool.get('name')=='Bash' and 'verify' in tool.get('input',{}).get('command','') and r['started_epoch']>=tool.get('_observed_epoch',float('inf')):
         for attempt in (root/'.deep-native/attempts').glob('*.json'):
          evidence=json.loads(attempt.read_text())
          if evidence.get('status')=='passed' and any(check.get('exit_code')==0 and 'run_checks.py' in check.get('argv',[]) for check in evidence.get('checks',[])) and evidence.get('attempt_id','IMPOSSIBLE') in content:native_proof=True
        if r and ('TASK_CHECK_RESULT' in content or native_proof) and not c.get('is_error'):seen_receipts.add(r['ended_epoch'])
        observation={'elapsed_seconds':time.monotonic()-started,'tool_use_id':c.get('tool_use_id'),'tool':tool,'source_hash':fingerprint(root),'current_receipt':r,'corroborated':bool(r and r['ended_epoch'] in seen_receipts),'is_error':c.get('is_error',False)}
        observations.append(observation)
        if n==1 and task['id'] in ['F1','R1'] and r and r['ended_epoch'] in seen_receipts:
         cp=checkpoint(root,arm) if task['id']=='R1' else None
         if task['id']=='F1' or cp:
          owner._signal_live(signal.SIGSTOP);owner.update();owner._signal_live(signal.SIGSTOP)
          g=grade(root,task,1,commit);full=grade(root,task,2,commit) if task['id']=='R1' else None
          if g['pass'] and (full is None or not full['pass']):
           qualified={'functional_receipt':r,'phase1_grade':g,'full_grade_before_kill':full,'checkpoint':cp,'elapsed_seconds':time.monotonic()-started,'trigger_tool':tool,'source_hash':fingerprint(root)};reason='qualified_SIGKILL';break
          owner._signal_live(signal.SIGCONT)
      if qualified:break
     if qualified:break
    if qualified:break
    if proc.poll() is not None and not selector.get_map():break
  finally:
   cleanup=owner.cleanup();selector.close();dump(artifact/'process_cleanup.json',cleanup)
   if buffer:log.write(buffer.decode('utf8','replace'))
 results=[e for e in events if e.get('type')=='result'];final=results[-1].get('result','') if results else ''
 (artifact/'final_response.txt').write_text(final);dump(artifact/'source_observations.json',observations)
 result={'session_id':sid,'exit_code':proc.returncode,'duration_seconds':time.monotonic()-started,'stop_reason':reason or 'normal_exit','qualified_interruption':qualified,'final_response':final,'cli_result':results[-1] if results else None,'final_hash':fingerprint(root),'corroborated_receipt_epochs':sorted(seen_receipts)}
 dump(artifact/'session.json',result)
 return result,events

def verify_freeze():
 for name,digest in json.loads((OUT/'freeze.json').read_text()).items():assert sha(HERE/name)==digest,'Freeze drift: '+name
 audit=json.loads((OUT/'audit.json').read_text());endpoint,model,_=config()
 assert (endpoint,model)==(audit['endpoint'],audit['model'])
 assert sha(Path(shutil.which('claude')).resolve())==audit['claude_sha256']
def changes(root,task,commit,n):
 names=set(git(root,'diff','--name-only',commit).splitlines()+git(root,'ls-files','--others','--exclude-standard').splitlines())
 def allowed(p):return p in task['files'] or p.startswith(('agent_tests/','docs/')) or p.endswith(('.md','.rst')) or (n==2 and p in ['benchmark_tests.py','benchmark_phase.json'])
 return sorted(names),sorted(p for p in names if not allowed(p))
def run_one(entry):
 verify_freeze();task=next(t for t in TASKS if t['id']==entry['task_id']);arm=entry['arm'];artifact=OUT/'runs'/entry['run_id']
 assert not artifact.exists(),'Refuse overwrite';artifact.mkdir(parents=True)
 base=Path(tempfile.mkdtemp(prefix='dn2-live-',dir='/private/tmp')).resolve();root=base/'workspace';home,tmp=setup_dirs(base)
 commit=prepare(root,task);cal=json.loads((OUT/'calibration.json').read_text());assert commit==cal[task['id']]['fixture_commit']
 endpoint,model,credential=config();relay=Relay(endpoint,credential);sessions=[];events=[];started=time.monotonic();n=1
 dump(artifact/'metadata.json',{**entry,'task':task,'fixture_commit':commit,'treatment_commit':ARMS[arm],'workspace':str(root),'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'model':model,'endpoint':endpoint,'budget':BUDGET})
 try:
  if arm!='A':
   helper=OUT/'treatments'/arm/'skills/deep-native/scripts/deep_native.py'
   install=cmd([PYTHON,helper,'--project',root,'install','--hooks'],root);dump(artifact/'installation.json',install);assert install['exit_code']==0
  expected=protected(root);dump(artifact/'protected_phase1.json',expected)
  staged=task['id'] in ['F1','R1']
  session,trace=live(root,task,arm,home,tmp,relay,model,artifact/'phase1',BUDGET['phase1_max_seconds'] if staged else BUDGET['wall_seconds'],BUDGET['phase1_max_attempts'] if staged else BUDGET['assistant_attempts'],commit,expected)
  sessions.append(session);events+=trace
  if staged and session['qualified_interruption']:
   (artifact/'interrupted.patch').write_text(git(root,'diff','--binary',commit));dump(artifact/'checkpoint_at_interrupt.json',session['qualified_interruption']['checkpoint'])
   before=fingerprint(root);phase(root,task,2);n=2;expected=protected(root);dump(artifact/'intervention.json',{'before_hash':before,'after_hash':fingerprint(root),'changed_files':['benchmark_tests.py','benchmark_phase.json'],'same_session':task['id']=='F1'});dump(artifact/'protected_phase2.json',expected)
   attempts=len([c for c in relay.calls if '/messages' in c['path'] and 'count_tokens' not in c['path']]);seconds=BUDGET['wall_seconds']-sum(s['duration_seconds'] for s in sessions);turns=BUDGET['assistant_attempts']-attempts
   if seconds>0 and turns>0:
    session,trace=live(root,task,arm,home,tmp,relay,model,artifact/'phase2',seconds,turns,commit,expected,n=2,resume=sessions[0]['session_id'] if task['id']=='F1' else None);sessions.append(session);events+=trace
  calls=relay.close();dump(artifact/'provider_calls.json',calls)
  independent=grade(root,task,2,commit);dump(artifact/'independent_grade.json',independent)
  paths,violations=changes(root,task,commit,n);integrity=protected(root)==expected
  final_receipt=receipt(root,n,expected);corroborated=bool(final_receipt and final_receipt['ended_epoch'] in sessions[-1]['corroborated_receipt_epochs'])
  outcome=independent['pass'] and not violations and integrity and (not staged or n==2) and (task['id'] not in ['E1','F1'] or corroborated)
  toolcalls=[c for e in events for c in e.get('message',{}).get('content',[]) if isinstance(c,dict) and c.get('type')=='tool_use']
  (artifact/'final.patch').write_text(git(root,'diff','--binary',commit))
  retained=artifact/'retained';retained.mkdir()
  for folder in ['.deep-native','.experiment','agent_tests']:
   if (root/folder).exists():shutil.copytree(root/folder,retained/folder,symlinks=True)
  for name in paths:
   p=root/name
   if p.is_file() and not p.is_symlink():d=retained/name;d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,d)
  result={**entry,'strict_pass':outcome,'functional_pass':independent['pass'],'final_verified':corroborated,'phase_reached':n,'scope_violations':violations,'protected_integrity':integrity,'files_changed':paths,'tool_calls':len(toolcalls),'duration_seconds':sum(s['duration_seconds'] for s in sessions),'provider_tokens':provider_tokens(calls),'cost':None,'sessions':sessions,'final_receipt':final_receipt}
  dump(artifact/'result.json',result)
  # Unexpected execution denials are an infrastructure stop, never an agent failure.
  raw='\n'.join((p.read_text() for p in artifact.rglob('transcript.jsonl')))
  denied=('Operation not permitted' in raw or 'Read-only file system' in raw)
  if denied:dump(OUT/'INFRASTRUCTURE_STOP.json',{'run':entry,'reason':'unexpected execution denial requires trace audit; no next run authorized by harness'});raise RuntimeError('Infrastructure stop')
  print(json.dumps({k:result[k] for k in ['run_id','strict_pass','tool_calls','duration_seconds']}),flush=True)
 finally:
  relay.close()
  # Keep the actual workspace for forensic inspection; sibling sandbox blocks reuse.
  dump(artifact/'retained_workspace.json',{'path':str(root),'preserved':True})

def main():
 assert not (OUT/'INFRASTRUCTURE_STOP.json').exists(),'Resolve infrastructure stop under a new freeze'
 schedule=json.loads((OUT/'schedule.json').read_text());assert len(schedule)==12
 for entry in schedule:
  p=OUT/'runs'/entry['run_id']
  if (p/'result.json').exists():continue
  assert not p.exists(),'Incomplete run requires explicit audit, never retry silently'
  run_one(entry)
if __name__=='__main__':main()
