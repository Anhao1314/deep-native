#!/usr/bin/env python3
"""Reproducible local A/B runner. Python 3.10+, macOS Seatbelt for live runs."""
import argparse
import hashlib
import json
import os
import platform
import random
import selectors
import shlex
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

from fixtures import TASKS, REPOS, manifest, seed, visible_tests, check_script
from transport import Relay, provider_tokens
from isolation import ProcessOwner, bootstrap_temp_dirs, sandbox_profile as isolated_profile

HERE=Path(__file__).resolve().parent
REPO=HERE.parent.parent
DN_COMMIT='fda3dd010e7de8f8c1ee1953e006e577464aa3d6'
ACTIVATION=manifest()['treatment_activation']

def dump(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
    tmp.replace(path)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def command(argv,cwd=None,timeout=90,env=None):
    started=time.monotonic()
    try:
        p=subprocess.run(argv,cwd=cwd,env=env,stdin=subprocess.DEVNULL,capture_output=True,
                         text=True,timeout=timeout)
        return {'argv':list(map(str,argv)), 'exit_code':p.returncode, 'stdout':p.stdout,
                'stderr':p.stderr,'duration_seconds':round(time.monotonic()-started,4)}
    except subprocess.TimeoutExpired:
        return {'argv':list(map(str,argv)), 'exit_code':124,'stdout':'','stderr':'TIMEOUT',
                'duration_seconds':round(time.monotonic()-started,4)}

def checked(argv,cwd=None):
    result=command(argv,cwd)
    if result['exit_code']:
        raise RuntimeError(json.dumps(result))
    return result['stdout'].strip()

def secret_config(path):
    data=json.loads(path.read_text())
    env=data.get('env',{})
    token=env.get('ANTHROPIC_AUTH_TOKEN') or env.get('ANTHROPIC_API_KEY')
    endpoint=env.get('ANTHROPIC_BASE_URL')
    model=env.get('ANTHROPIC_MODEL') or data.get('model')
    if not token or not endpoint or not model:
        raise ValueError('Explicit provider configuration is missing; no credential discovery attempted.')
    if endpoint != 'https://api.deepseek.com/anthropic':
        raise ValueError('This protocol requires the audited official DeepSeek endpoint.')
    return endpoint,model,token

def cache_repo(cache,name):
    repo=cache/name
    source=REPOS[name]
    if not repo.exists():
        checked(['git','clone',source['url'],str(repo)])
    checked(['git','cat-file','-e',source['commit']+'^{commit}'],repo)
    return repo

def prepare(root,task,cache,python):
    root.mkdir(parents=True)
    archive=subprocess.run(['git','-C',str(cache_repo(cache,task['repo'])),'archive',REPOS[task['repo']]['commit']],capture_output=True,check=True).stdout
    subprocess.run(['tar','-x','-C',str(root)],input=archive,check=True)
    # Fail closed if upstream introduces implicit experimental instructions.
    if any(root.rglob('CLAUDE.md')) or any(root.rglob('AGENTS.md')) or (root/'.claude').exists():
        raise ValueError('Upstream instructions require a new audited protocol.')
    seed(root,task)
    (root/'benchmark_tests.py').write_text(visible_tests(task))
    (root/'benchmark_check.py').write_text(check_script(task))
    checked(['git','init','-q'],root)
    checked(['git','config','user.name','Benchmark Fixture'],root)
    checked(['git','config','user.email','benchmark@example.invalid'],root)
    checked(['git','add','-A'],root)
    env={**os.environ,'GIT_AUTHOR_DATE':'2026-10-06T00:00:00+0000','GIT_COMMITTER_DATE':'2026-10-06T00:00:00+0000'}
    result=command(['git','commit','-qm','Frozen fixture '+task['id']],root,env=env)
    assert result['exit_code']==0
    (root/'.git/info/exclude').write_text('\n.claude/\n.deep-native/\n.deep-native.json\n.check-started\n__pycache__/\n*.pyc\n.pytest_cache/\n')
    # Identical fixture commit across every arm/repeat.
    return checked(['git','rev-parse','HEAD'],root)

def protected_hashes(root):
    names=checked(['git','ls-files','-z'],root).split('\0')
    return {name:digest((root/name).read_bytes()) for name in names if name and
            ((root/name).is_file()) and (name.startswith('tests/') or name.startswith('benchmark_'))}

def allowed_changes(root,task,fixture_commit=None):
    base=fixture_commit or 'HEAD'
    changed=checked(['git','diff','--no-ext-diff','--no-textconv','--name-only',base],root).splitlines()
    untracked=checked(['git','ls-files','--others','--exclude-standard'],root).splitlines()
    paths=sorted(set(changed+untracked))
    allowed=lambda p:p in task['files'] or p.startswith('agent_tests/') or p.startswith('docs/') or p.endswith(('.md','.rst'))
    return paths,[p for p in paths if not allowed(p)]

def grade(root,task,python,phase=2,fixture_commit=None):
    """Copy tracked submission bytes into a fresh grader directory, no agent state."""
    with tempfile.TemporaryDirectory(prefix='dn-independent-grade-') as temp:
        base_dir=Path(temp).resolve();dest=base_dir/'workspace';dest.mkdir()
        home=base_dir/'home';home.mkdir();tmp=base_dir/'tmp';tmp.mkdir()
        base=fixture_commit or checked(['git','rev-parse','HEAD'],root)
        baseline_files=set(checked(['git','ls-tree','-rz','--name-only',base],root).split('\0'))-{''}
        current_files=set(checked(['git','ls-files','-z'],root).split('\0'))-{''}
        for name in sorted(baseline_files | current_files):
            if not name:continue
            source=root/name
            if source.is_symlink() or not source.is_file():
                return {'pass':False,'reason':'tracked_file_missing_or_symlink','path':name}
            target=dest/name;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,target)
        # New implementation modules/tests are allowed; never include arbitrary state.
        for name in checked(['git','ls-files','--others','--exclude-standard','-z'],root).split('\0'):
            if not name:continue
            source=root/name
            if source.is_symlink():
                return {'pass':False,'reason':'untracked_symlink','path':name}
            if source.is_file():
                target=dest/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
        # The immutable fixture supplies canonical upstream tests/checks, even if
        # the candidate altered its index/HEAD. Such edits still fail scope/hash checks.
        for name in sorted(baseline_files):
            if name.startswith('tests/') or name.startswith('benchmark_'):
                payload=subprocess.run(['git','cat-file','blob',base+':'+name],cwd=root,capture_output=True,check=True).stdout
                (dest/name).write_bytes(payload)
        env={'PATH':str(python.parent)+':/usr/bin:/bin:/usr/sbin:/sbin','HOME':str(home),'TMPDIR':str(tmp),
             'LANG':'en_US.UTF-8','PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1','PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1'}
        wrapper=[]
        if platform.system()=='Darwin':
            profile=base_dir/'grader.sb'
            profile.write_text(isolated_profile(dest,home,python.parent.parent,port=None,read_only_paths=[HERE/'acceptance.py']))
            wrapper=['sandbox-exec','-D','CLI_PID=0','-f',str(profile)]
        contract=command(wrapper+[str(python),str(HERE/'acceptance.py'),task['id'],str(phase)],dest,60,env)
        regression=command(wrapper+[str(python),'-m','unittest','discover','-s','tests'],dest,120,env) if task['repo']=='more' else command(wrapper+[str(python),'-m','pytest','-q','tests/test_strutils.py','tests/test_iterutils.py'],dest,60,env)
        if (dest/'agent_tests').exists():
            new_tests=command(wrapper+[str(python),'-m','pytest','-q','agent_tests'],dest,60,env)
        elif task.get('regression_tests_required'):
            new_tests={'exit_code':5,'stdout':'','stderr':'Required new regression tests are missing.'}
        else:
            new_tests={'exit_code':0,'stdout':'','stderr':'No new regression tests supplied; not required by this task.'}
        return {'pass':contract['exit_code']==0 and regression['exit_code']==0 and new_tests['exit_code']==0,
                'contract':contract,'upstream_regression':regression,'new_regression_tests':new_tests}

def sandbox_profile(root,home,dependencies,port):
    return isolated_profile(root,home,dependencies,port)

def agent_env(home,tmp,python,relay,model):
    # No inherited credentials, config, PYTHONPATH, git credentials, shell startup.
    return {'HOME':str(home),'CLAUDE_CONFIG_DIR':str(home/'.claude'),
            'PATH':str(python.parent)+':'+str(Path(shutil.which('claude')).parent)+':/usr/bin:/bin:/usr/sbin:/sbin',
            'TMPDIR':str(tmp),'CLAUDE_CODE_TMPDIR':str(tmp),'LANG':'en_US.UTF-8','USER':'benchmark',
            'ANTHROPIC_AUTH_TOKEN':'benchmark-local-relay', 'ANTHROPIC_BASE_URL':relay.url,
            'ANTHROPIC_MODEL':model,'ANTHROPIC_DEFAULT_OPUS_MODEL':model,
            'ANTHROPIC_DEFAULT_SONNET_MODEL':model,'ANTHROPIC_DEFAULT_HAIKU_MODEL':model,
            'CLAUDE_CODE_SUBAGENT_MODEL':model,'CLAUDE_CODE_EFFORT_LEVEL':'max',
            'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC':'1','CLAUDE_CODE_DISABLE_AUTO_MEMORY':'1',
            'DISABLE_AUTOUPDATER':'1','PYTHONNOUSERSITE':'1','PYTHONDONTWRITEBYTECODE':'1',
            'BASH_ENV':'/dev/null','ZDOTDIR':str(home)}

def live_session(root,home,tmp,python,relay,model,condition,prompt,artifact,seconds,turns,
                 recovery=False,resume=None,previous_verified_hash=None):
    if turns<=0 or seconds<=0:raise ValueError('Session budget exhausted; no extra turn granted.')
    sid=str(uuid.uuid4())
    argv=['claude','-p',prompt,'--model',model,'--effort','max',
          '--setting-sources','project,local','--strict-mcp-config','--mcp-config','{"mcpServers":{}}',
          '--tools','Bash,Read,Edit,Write,Glob,Grep,Skill',
          '--allowedTools','Bash,Read,Edit,Write,Glob,Grep,Skill',
          '--permission-mode','dontAsk','--output-format','stream-json','--verbose',
          '--include-hook-events','--max-turns',str(turns),'--session-id',sid]
    if resume:
        # Same conversation for the staleness second stage; recovery uses a new one.
        argv=argv[:-2]+['--resume',resume]
    if condition=='B':argv+=['--append-system-prompt',ACTIVATION]
    profile=root.parent/'sandbox.sb'
    bootstrap_temp_dirs(root)
    profile.write_text(sandbox_profile(root,home,python.parent.parent,relay.server.server_port))
    env=agent_env(home,tmp,python,relay,model)
    argv=['/bin/sh','-c','profile=$1; shift; exec sandbox-exec -D "CLI_PID=$$" -f "$profile" "$@"',
          'benchmark-launcher',str(profile)]+argv
    artifact.mkdir(parents=True,exist_ok=True)
    (artifact/'prompt.txt').write_text(prompt)
    dump(artifact/'command.json',argv)
    started=time.monotonic();events=[];buffer=b'';interrupted=False;reason=None
    baseline=source_fingerprint(root,task_files=None)
    observations=[];tool_inputs={};last_verified_hash=previous_verified_hash
    operator_interrupted=False
    writes_seen=False;tool_results_after_write=0;ids=set()
    with (artifact/'transcript.jsonl').open('w') as transcript,(artifact/'stderr.txt').open('w') as stderr:
        proc=subprocess.Popen(argv,cwd=root,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                              stderr=stderr,start_new_session=True)
        owner=ProcessOwner(proc);proc._benchmark_owner=owner;next_owner_poll=0
        selector=selectors.DefaultSelector();selector.register(proc.stdout,selectors.EVENT_READ)
        try:
            while True:
                elapsed=time.monotonic()-started
                if elapsed>=next_owner_poll:
                    owner.update();next_owner_poll=elapsed+.5
                if elapsed>=seconds:
                    reason='wall_budget';kill_group(proc);break
                for key,_ in selector.select(timeout=.2):
                    data=os.read(key.fileobj.fileno(),65536)
                    if not data:
                        selector.unregister(key.fileobj);continue
                    buffer+=data
                    while b'\n' in buffer:
                        line,buffer=buffer.split(b'\n',1)
                        text=line.decode('utf-8','replace');transcript.write(text+'\n');transcript.flush()
                        try:event=json.loads(text)
                        except ValueError:continue
                        events.append(event)
                        if event.get('type')=='assistant':ids.add(event.get('message',{}).get('id'))
                        for c in event.get('message',{}).get('content',[]):
                            if not isinstance(c,dict):continue
                            if c.get('type')=='tool_use':tool_inputs[c.get('id')]=c
                            if c.get('type')=='tool_result':
                                owner.update()
                                tool=tool_inputs.get(c.get('tool_use_id'),{})
                                cmd=tool.get('input',{}).get('command','')
                                verify=tool.get('name')=='Bash' and verification_command(cmd)
                                fingerprint=source_fingerprint(root,None)
                                successful=verify and result_success(c)
                                observations.append({'tool_use_id':c.get('tool_use_id'),'source_fingerprint':fingerprint,
                                    'verification_command':verify,'verification_success':successful,
                                    'tool_error':c.get('is_error',False),'timestamp':event.get('timestamp')})
                                if successful:last_verified_hash=fingerprint
                        if recovery and event.get('type')=='user':
                            if source_fingerprint(root,None)!=baseline:
                                if writes_seen:tool_results_after_write+=1
                                writes_seen=True
                            if writes_seen and tool_results_after_write>=1:
                                interrupted=True;reason='scheduled_source_mutation_interrupt';kill_group(proc);break
                    if interrupted:break
                if interrupted:break
                if recovery and elapsed>=90:
                    interrupted=True;reason='scheduled_90_second_interrupt';kill_group(proc);break
                if proc.poll() is not None and not selector.get_map():break
            proc.wait(timeout=10)
        except KeyboardInterrupt:
            operator_interrupted=True;reason='operator_interrupt';kill_group(proc);proc.wait(timeout=10)
        finally:
            cleanup=owner.cleanup();selector.close()
            dump(artifact/'process_cleanup.json',cleanup)
        if buffer:
            transcript.write(buffer.decode('utf-8','replace'))
    results=[e for e in events if e.get('type')=='result']
    final=results[-1].get('result','') if results else ''
    (artifact/'final_response.txt').write_text(final)
    dump(artifact/'source_observations.json',observations)
    result={'session_id':sid if not resume else resume,'exit_code':proc.returncode,
            'duration_seconds':round(time.monotonic()-started,4), 'interrupted':interrupted,
            'stop_reason':reason or (results[-1].get('terminal_reason') if results else 'no_result'),
            'observed_assistant_messages':len(ids), 'final_response':final,
            'cli_result':results[-1] if results else None,
            'last_observed_verified_source_hash':last_verified_hash,
            'final_source_hash':source_fingerprint(root,None),
            'stale_observed_verification':last_verified_hash is not None and last_verified_hash!=source_fingerprint(root,None),
            'operator_interrupted':operator_interrupted}
    dump(artifact/'session.json',result)
    if operator_interrupted:raise KeyboardInterrupt
    return result,events

def kill_group(proc):
    owner=getattr(proc,'_benchmark_owner',None)
    if owner is None:owner=ProcessOwner(proc);proc._benchmark_owner=owner
    return owner.cleanup()

def source_fingerprint(root,task_files=None):
    names=task_files or [str(p.relative_to(root)) for d in ['boltons','more_itertools','agent_tests']
                        for p in (root/d).rglob('*') if p.is_file() and p.suffix in {'.py','.pyi'}]
    h=hashlib.sha256()
    for name in sorted(names):
        p=root/name
        h.update(name.encode()+b'\0');h.update(p.read_bytes() if p.is_file() else b'MISSING');h.update(b'\0')
    return h.hexdigest()

def behavior(events):
    tools={};sequence=[];last_edit=-1;last_verify=-1;failed_indices=[];success_indices=[]
    for e in events:
        for content in e.get('message',{}).get('content',[]):
            if not isinstance(content,dict):continue
            if content.get('type')=='tool_use':
                name=content.get('name');inp=content.get('input',{});cmd=inp.get('command','')
                kind='other'
                if name in ['Read','Glob','Grep'] or (name=='Bash' and any(x in cmd for x in ['cat ','sed ','rg ','grep ','git diff','git status'])):kind='inspect'
                if name in ['Edit','Write'] or (name=='Bash' and any(x in cmd for x in ['write_text','write_bytes','sed -i',"open(", 'cat >','apply_patch'])):kind='edit'
                if name=='Bash' and verification_command(cmd):kind='verify'
                item={'name':name,'input':inp,'kind':kind,'index':len(sequence),'success':None}
                tools[content.get('id')]=item;sequence.append(item)
                if kind=='edit':last_edit=item['index']
                if kind=='verify':last_verify=item['index']
            elif content.get('type')=='tool_result':
                tool=tools.get(content.get('tool_use_id'))
                if tool:
                    tool['success']=result_success(content)
                    if tool['kind']=='verify':
                        (success_indices if tool['success'] else failed_indices).append(tool['index'])
    first_edit=next((i for i,t in enumerate(sequence) if t['kind']=='edit'),len(sequence))
    return {'tool_calls':len(sequence),'inspection_before_edit':any(t['kind']=='inspect' for t in sequence[:first_edit]),
            'reproduction_before_edit':any(t['kind']=='verify' for t in sequence[:first_edit]),
            'executed_verification':any(t['kind']=='verify' for t in sequence),
            'successful_verification':any(t['kind']=='verify' and t['success'] for t in sequence),
            'continued_after_failed_verification':any(s>f for s in success_indices for f in failed_indices) if failed_indices else None,
            'edit_after_last_verification':last_edit>last_verify>=0,
            'skill_invoked':any(t['name']=='Skill' and t['input'].get('skill','').endswith('deep-native') and t['success'] for t in sequence),
            'risk_reported':None,'fabricated_verification':None,'events':sequence}

def verification_command(cmd):
    try:
        lexer=shlex.shlex(cmd,posix=True,punctuation_chars=';&|()\n');lexer.whitespace_split=True
        lexer.whitespace=' \t\r'
        tokens=list(lexer)
    except ValueError:return False
    segments=[];segment=[]
    for token in tokens:
        if token and all(c in ';&|()\n' for c in token):
            if segment:segments.append(segment);segment=[]
        else:segment.append(token)
    if segment:segments.append(segment)
    for args in segments:
        while args and ('=' in args[0] or args[0] in ['env','command','then','do','exec']):args=args[1:]
        if not args:continue
        exe=args[0].rsplit('/',1)[-1]
        if exe in ['pytest','benchmark_check.py','benchmark_tests.py']:return True
        if not re.fullmatch(r'python(?:\d+(?:\.\d+)*)?',exe):continue
        helper=next((i for i,t in enumerate(args[1:],1) if t.endswith('deep_native.py')),None)
        if helper is not None:
            subcommands={'configure','begin','checkpoint','finish','status','doctor','adopt','block','verify'}
            actual=next((t for t in args[helper+1:] if t in subcommands),None)
            if actual=='verify':return True
            continue
        if any(args[i]=='-m' and args[i+1] in ['unittest','pytest','doctest'] for i in range(len(args)-1)):return True
        script=next((t for t in args[1:] if not t.startswith('-')),None)
        if script and script.rsplit('/',1)[-1] in ['benchmark_check.py','benchmark_tests.py']:return True
    return False

def result_success(content):
    if content.get('is_error',False):return False
    text=content.get('content','')
    if not isinstance(text,str):text=json.dumps(text)
    # Piped output can conceal nonzero exits from Claude's tool-level flag.
    return not re.search(r'FAILED \(|Traceback \(most recent call last\)|Exit code [1-9]|\b\d+ failed\b|\bno tests ran\b|Ran 0 tests|"status"\s*:\s*"failed"|Verification refused',text,re.I)

def completion_declaration(final):
    lines=[line.strip() for line in final.splitlines() if line.strip()]
    if not lines:return None
    marker=re.fullmatch(r'STATUS:\s*(DONE|BLOCKED)',lines[-1])
    return (marker.group(1)=='DONE') if marker else None

def remaining_budget(budget,sessions):
    return (max(0,budget['assistant_turns']-sum(s['observed_assistant_messages'] for s in sessions)),
            max(0,budget['wall_seconds']-sum(s['duration_seconds'] for s in sessions)))

def make_schedule(seed_value=20261006):
    rng=random.Random(seed_value);schedule=[]
    for repeat in range(1,4):
        tasks=list(TASKS);rng.shuffle(tasks)
        for task in tasks:
            arms=['A','B'];rng.shuffle(arms)
            for arm in arms:schedule.append({'run_id':f"{task['id']}-r{repeat}-{arm}",'task_id':task['id'],'repeat':repeat,'condition':arm})
    return schedule

def audit(config,python,out):
    endpoint,model,_=secret_config(config)
    data=json.loads(config.read_text())
    env=data.get('env',{})
    report={'client_date':'2026-10-06','platform':platform.platform(),'machine':platform.machine(),
            'python':checked([str(python),'--version']),'python_base_prefix':sys.base_prefix,
            'python_binary_sha256':digest(python.resolve().read_bytes()),
            'node':checked(['node','--version']),'git':checked(['git','--version']),
            'claude':checked(['claude','--version']),'claude_binary_sha256':digest(Path(shutil.which('claude')).resolve().read_bytes()),
            'deep_native_commit':DN_COMMIT,'upstream_endpoint':endpoint,'requested_model':model,
            'original_config_keys':list(data),'original_env_names':sorted(env),
            'original_hooks':list(data.get('hooks',{})), 'original_config_sha256':digest(config.read_bytes()),
            'managed_settings_present':Path('/Library/Application Support/ClaudeCode').exists(),
            'global_claude_md_present':(Path.home()/'.claude/CLAUDE.md').exists(),
            'global_skills_present':(Path.home()/'.claude/skills').exists(),
            'global_plugins_present':(Path.home()/'.claude/plugins').exists(),
            'isolation':'Fresh HOME, config, tmp, worktree; project/local settings only; strict empty MCP; OS denies personal config and benchmark artifacts; loopback relay holds upstream auth in parent memory.',
            'allowed_tools':['Bash','Read','Edit','Write','Glob','Grep','Skill'],
            'effort':'max','memory':False,'budget':manifest()['budget'],
            'cost':'unavailable: CLI costBasis unknown; no provider billing receipt',
            'packages':json.loads(checked([str(python),'-c','import importlib.metadata,json; print(json.dumps({k:importlib.metadata.version(k) for k in ["pytest","pluggy","packaging","iniconfig"]}))']))}
    if report['managed_settings_present']:raise ValueError('Managed settings need explicit audit before running.')
    dump(out/'audit.json',report)
    return report

def validate_environment(out,python):
    expected=json.loads((out/'audit.json').read_text())
    values={'claude':checked(['claude','--version']),
            'claude_binary_sha256':digest(Path(shutil.which('claude')).resolve().read_bytes()),
            'python':checked([str(python),'--version']),
            'python_binary_sha256':digest(python.resolve().read_bytes()),
            'git':checked(['git','--version']),'node':checked(['node','--version']),
            'packages':json.loads(checked([str(python),'-c','import importlib.metadata,json;print(json.dumps({k:importlib.metadata.version(k) for k in ["pytest","pluggy","packaging","iniconfig"]}))']))}
    for name,actual in values.items():
        if expected.get(name)!=actual:raise ValueError('Frozen environment changed: '+name)

def freeze(out,python,cache,config):
    out.mkdir(parents=True,exist_ok=True)
    if (out/'freeze.json').exists():raise ValueError('Campaign already frozen; choose a new output directory.')
    audit(config,python,out)
    dump(out/'tasks.json',manifest());dump(out/'schedule.json',make_schedule())
    skill=subprocess.run(['git','-C',str(REPO),'archive',DN_COMMIT,'skills/deep-native'],capture_output=True,check=True).stdout
    frozen=out/'frozen-treatment';frozen.mkdir()
    subprocess.run(['tar','-x','-C',str(frozen)],input=skill,check=True)
    baselines={}
    for task in TASKS:
        with tempfile.TemporaryDirectory(prefix='dn-fixture-preflight-') as temp:
            root=Path(temp)/'repo';commit=prepare(root,task,cache,python)
            result=grade(root,task,python)
            assert not result['pass'], 'Task already passes before agent: '+task['id']
            baselines[task['id']]={'fixture_commit':commit,'tests_before':result,
                                  'protected_hashes':protected_hashes(root)}
    dump(out/'baselines.json',baselines)
    files=[HERE/name for name in ['fixtures.py','tasks.json','acceptance.py','harness.py','transport.py',
                                 'analysis.py','isolation.py','audit_evidence.py']]
    lock={str(p.relative_to(HERE)):digest(p.read_bytes()) for p in files}
    snapshot=out/'frozen-harness'
    for p in files:
        target=snapshot/p.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    dump(out/'freeze.json',{'protocol_sha256':lock,'deep_native_commit':DN_COMMIT,
                           'treatment_sha256':{str(p.relative_to(frozen)):digest(p.read_bytes()) for p in frozen.rglob('*') if p.is_file()},
                           'audit_sha256':digest((out/'audit.json').read_bytes()),
                           'baselines_sha256':digest((out/'baselines.json').read_bytes()),
                           'schedule_sha256':digest((out/'schedule.json').read_bytes()),
                           'tasks_sha256':digest((out/'tasks.json').read_bytes()),
                           'frozen_at_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})
    print('FROZEN',out,flush=True)

def verify_freeze(out):
    lock=json.loads((out/'freeze.json').read_text())
    for name,expected in lock['protocol_sha256'].items():
        if digest((HERE/name).read_bytes())!=expected:raise ValueError('Frozen protocol changed: '+name)
    for name,key in [('schedule.json','schedule_sha256'),('tasks.json','tasks_sha256')]:
        if digest((out/name).read_bytes())!=lock[key]:raise ValueError('Frozen campaign changed: '+name)
    for name,key in [('audit.json','audit_sha256'),('baselines.json','baselines_sha256')]:
        if key in lock and digest((out/name).read_bytes())!=lock[key]:raise ValueError('Frozen campaign changed: '+name)
    for name,expected in lock.get('treatment_sha256',{}).items():
        if digest((out/'frozen-treatment'/name).read_bytes())!=expected:raise ValueError('Frozen treatment changed: '+name)

def run_one(entry,out,python,cache,config):
    task=next(t for t in TASKS if t['id']==entry['task_id'])
    artifact=out/'runs'/entry['run_id']
    if artifact.exists():raise ValueError('Existing run retained; refusing overwrite: '+entry['run_id'])
    artifact.mkdir(parents=True)
    endpoint,model,credential=secret_config(config)
    frozen_audit=json.loads((out/'audit.json').read_text())
    if (endpoint,model)!=(frozen_audit['upstream_endpoint'],frozen_audit['requested_model']):
        raise ValueError('Provider endpoint/model changed after freeze')
    started=time.monotonic();events=[];sessions=[]
    budget=manifest()['budget']
    base=Path(tempfile.mkdtemp(prefix='dn-live-',dir='/private/tmp'))
    root=base/'workspace';home=base/'home';tmp=base/'tmp'
    (home/'.claude').mkdir(parents=True);tmp.mkdir()
    relay=Relay(endpoint,credential)
    dump(artifact/'metadata.json',{**entry,'task':task,'deep_native_commit':DN_COMMIT,
          'repository':REPOS[task['repo']], 'model':model,'endpoint':endpoint,'workspace':str(root),
          'environment':agent_env(home,tmp,python,relay,model),'budget':budget,
          'started_at_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})
    try:
        commit=prepare(root,task,cache,python)
        baseline=json.loads((out/'baselines.json').read_text())[task['id']]
        assert commit==baseline['fixture_commit']
        dump(artifact/'tests_before.json',baseline['tests_before'])
        protected=protected_hashes(root)
        if entry['condition']=='B':
            helper=out/'frozen-treatment/skills/deep-native/scripts/deep_native.py'
            install=command([str(python),str(helper),'--project',str(root),'install','--hooks'],root)
            dump(artifact/'installation.json',install)
            assert install['exit_code']==0
        else:
            assert not (root/'.claude').exists() and not (root/'.deep-native').exists()
        first_budget=18 if task.get('phases') else budget['assistant_turns']
        session,trace=live_session(root,home,tmp,python,relay,model,entry['condition'],task['prompt'],artifact/'phase1',
            budget['wall_seconds'],first_budget,recovery=task.get('recovery',False))
        sessions.append(session);events+=trace
        phase1=None
        if task.get('phases'):
            phase1=grade(root,task,python,phase=1,fixture_commit=commit);dump(artifact/'phase1_independent_grade.json',phase1)
            before=source_fingerprint(root,task['files'])
            prompt=task['continuation']
            remaining,seconds=remaining_budget(budget,sessions)
            if seconds>0 and remaining>0:
                session2,trace=live_session(root,home,tmp,python,relay,model,entry['condition'],prompt,artifact/'phase2',seconds,remaining,resume=session['session_id'],previous_verified_hash=session['last_observed_verified_source_hash'])
                sessions.append(session2);events+=trace
            dump(artifact/'staleness_intervention.json',{'phase1_pass':phase1['pass'],'fingerprint_before':before,
                  'fingerprint_after':source_fingerprint(root,task['files']),'actual_later_source_change':before!=source_fingerprint(root,task['files'])})
        elif task.get('recovery') and session['interrupted']:
            state_path=root/'.deep-native/state.json'
            state=json.loads(state_path.read_text()) if state_path.exists() else None
            if state:dump(artifact/'interrupted-state.json',state)
            (artifact/'interrupted_patch.diff').write_text(checked(['git','diff','HEAD'],root)+'\n'+untracked_diff(root))
            dump(artifact/'interruption.json',{'actual_signal':'SIGKILL','reason':session['stop_reason'],
                   'source_fingerprint':source_fingerprint(root,task['files']),
                   'state_present':state is not None,'checkpoint_note_present':bool(state and state.get('note'))})
            remaining,seconds=remaining_budget(budget,sessions)
            if seconds>0 and remaining>0:
                session2,trace=live_session(root,home,tmp,python,relay,model,entry['condition'],
                    'Continue working on this task:\n'+task['prompt'],artifact/'phase2',seconds,remaining)
                sessions.append(session2);events+=trace
        api_calls=relay.close()
        dump(artifact/'api_calls.json',api_calls)
        after=grade(root,task,python,fixture_commit=commit);dump(artifact/'tests_after.json',after)
        files,forbidden=allowed_changes(root,task,fixture_commit=commit)
        changed_tests=[name for name,value in protected.items() if not (root/name).is_file() or digest((root/name).read_bytes())!=value]
        (artifact/'patch.diff').write_text(checked(['git','diff','--no-ext-diff','--no-textconv',commit],root)+'\n'+untracked_diff(root))
        b=behavior(events);dump(artifact/'behavior.json',b)
        final=sessions[-1]['final_response'];(artifact/'final_response.txt').write_text(final)
        b['risk_reported']=bool(re.search(r'\b(risks?|limitations?|unverified|not tested|untested|blocked)\b',final,re.I))
        b['verification_claim_without_detected_success']=bool(re.search(r'\b(passed|passing|tests? green|all checks|OK)\b',final,re.I)) and not b['successful_verification']
        dump(artifact/'behavior.json',b)
        done=completion_declaration(final)
        passed=after['pass'] and not forbidden and not changed_tests
        models={c['response_model'] for c in api_calls if c.get('response_model')}
        inits=[e for e in events if e.get('subtype')=='init']
        control_clean=bool(inits) and all('deep-native' not in e.get('skills',[]) for e in inits) if entry['condition']=='A' else None
        treatment_valid=(control_clean if entry['condition']=='A' else b['skill_invoked'])
        result={**entry,'category':task['category'],'task_success':'PASS' if passed else 'FAIL',
                'declared_done':done,'actually_valid':passed,
                'false_completion':done is True and not passed,
                'duration_seconds':round(sum(s['duration_seconds'] for s in sessions),4),
                'including_setup_and_grade_seconds':round(time.monotonic()-started,4),
                'tokens':provider_tokens(api_calls),'api_cost_usd':None,'api_cost_status':'unavailable',
                'response_models':sorted(models),'treatment_activation_observed':treatment_valid,
                'control_clean':control_clean,
                'recovery_interrupted':any(s['interrupted'] for s in sessions),
                'sessions':len(sessions),'fixture_commit':commit,'files_changed':files,
                'forbidden_changes':forbidden,'protected_test_changes':changed_tests,
                'patch_sha256':digest((artifact/'patch.diff').read_bytes()),
                'tool_calls':b['tool_calls'],'behavior':{k:v for k,v in b.items() if k!='events'},
                'lines_added':sum(l.startswith('+') and not l.startswith('+++') for l in (artifact/'patch.diff').read_text().splitlines()),
                'lines_removed':sum(l.startswith('-') and not l.startswith('---') for l in (artifact/'patch.diff').read_text().splitlines()),
                'phase1_pass':phase1['pass'] if phase1 else None,
                'phase1_successful_verification':bool(sessions[0]['last_observed_verified_source_hash']) if phase1 else None,
                'actual_later_source_change':before!=source_fingerprint(root,task['files']) if phase1 else None,
                'total_observed_assistant_messages':sum(s['observed_assistant_messages'] for s in sessions),
                'stop_reasons':[s['stop_reason'] for s in sessions],
                'stale_observed_verification':sessions[-1]['stale_observed_verification'],
                'stale_completion_claim':done is True and sessions[-1]['stale_observed_verification']}
        dump(artifact/'result.json',result)
        # Treatment state is evidence only; never used by the independent grader.
        if (root/'.deep-native').exists():shutil.copytree(root/'.deep-native',artifact/'deep-native-state')
        if (root/'.deep-native.json').exists():shutil.copyfile(root/'.deep-native.json',artifact/'deep-native-contract.json')
        print(entry['run_id'],result['task_success'],'seconds',result['duration_seconds'],flush=True)
        return result
    finally:
        # Keep failures and partial provider logs; never silently discard a run.
        dump(artifact/'api_calls.json',relay.close())
        # Workspace retained locally for forensic review; it is not reused.
        (artifact/'local_workspace.txt').write_text(str(base)+'\n')
        dump(artifact/'artifact_hashes.json',{str(p.relative_to(artifact)):digest(p.read_bytes()) for p in artifact.rglob('*') if p.is_file() and p.name!='artifact_hashes.json'})

def untracked_diff(root):
    parts=[]
    for name in checked(['git','ls-files','--others','--exclude-standard'],root).splitlines():
        p=root/name
        if p.is_file() and not p.is_symlink():
            text=p.read_text(errors='replace').splitlines()
            parts.append('diff --git a/'+name+' b/'+name+'\nnew file mode 100644\n--- /dev/null\n+++ b/'+name+'\n@@ -0,0 +1,'+str(len(text))+' @@\n'+'\n'.join('+'+l for l in text)+'\n')
    return ''.join(parts)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['audit','freeze','run','analyze'])
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--python',type=Path,default=Path(sys.executable))
    parser.add_argument('--cache',type=Path,default=Path('/private/tmp/dn-benchmark-cache'))
    parser.add_argument('--provider-config',type=Path,default=Path.home()/'.claude/settings.json')
    parser.add_argument('--limit',type=int,default=60)
    args=parser.parse_args();args.output=args.output.resolve();args.python=args.python.absolute();args.cache=args.cache.resolve()
    args.cache.mkdir(parents=True,exist_ok=True)
    if args.action=='audit':audit(args.provider_config,args.python,args.output)
    elif args.action=='freeze':freeze(args.output,args.python,args.cache,args.provider_config)
    elif args.action=='run':
        if platform.system()!='Darwin' or not shutil.which('sandbox-exec'):
            raise ValueError('Live execution requires the documented macOS isolation profile.')
        verify_freeze(args.output)
        audit_data=json.loads((args.output/'audit.json').read_text())
        validate_environment(args.output,args.python)
        schedule=json.loads((args.output/'schedule.json').read_text())
        count=0
        for entry in schedule:
            run_path=args.output/'runs'/entry['run_id']
            if (run_path/'result.json').exists():continue
            if count>=args.limit:break
            try:
                verify_freeze(args.output);validate_environment(args.output,args.python)
                run_one(entry,args.output,args.python,args.cache,args.provider_config)
            except (Exception,KeyboardInterrupt) as exc:
                dump(args.output/'campaign_stop.json',{'run_id':entry['run_id'],'error_type':type(exc).__name__,
                     'stop_requested_by_user':isinstance(exc,KeyboardInterrupt),
                     'reason':'Operator interrupt or harness/environment error. Partial artifacts retained; no automatic retry.'})
                raise
            count+=1
    else:
        from analysis import generate
        generate(args.output)

if __name__=='__main__':main()
