"""Shared environment for all three arms. No provider credentials in children."""
import json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
from isolation import sandbox_profile as original_profile

def native_git():
    p=Path('/Library/Developer/CommandLineTools/usr/bin/git')
    return p if p.exists() else Path(shutil.which('git'))

def env_for(root,home,tmp,python,relay_url=None,model=None,sid=None):
    tools=root.parent/'tools';tools.mkdir(exist_ok=True)
    # BSD mktemp without a template uses confstr's host temp directory. Select
    # its documented -p option for all invocations; explicit templates remain intact.
    wrapper=tools/'mktemp'
    wrapper.write_text('#!/bin/sh\nexec /usr/bin/mktemp -p "$TMPDIR" "$@"\n')
    wrapper.chmod(0o755)
    result={'HOME':str(home),'CLAUDE_CONFIG_DIR':str(home/'.claude'),
        'PATH':str(tools)+':'+str(python.parent)+':'+str(Path(shutil.which('claude')).parent)+':'+str(native_git().parent)+':/usr/bin:/bin:/usr/sbin:/sbin',
        'TMPDIR':str(tmp)+'/', 'TMP':str(tmp),'TEMP':str(tmp),
        'TMPPREFIX':str(tmp/'zsh'), 'CLAUDE_CODE_TMPDIR':str(tmp),
        'PYTHONPATH':str(root/'src'),'PYTHONNOUSERSITE':'1','PYTHONDONTWRITEBYTECODE':'1',
        'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1','LANG':'en_US.UTF-8','USER':'benchmark',
        'BASH_ENV':'/dev/null','ZDOTDIR':str(home),'DISABLE_AUTOUPDATER':'1',
        'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC':'1','CLAUDE_CODE_DISABLE_AUTO_MEMORY':'1',
        'CLAUDE_CODE_EFFORT_LEVEL':'max'}
    if sid:result['CLAUDE_SESSION_ID']=sid
    if relay_url:result.update(ANTHROPIC_AUTH_TOKEN='benchmark-local-relay',ANTHROPIC_BASE_URL=relay_url,
        ANTHROPIC_MODEL=model,ANTHROPIC_DEFAULT_OPUS_MODEL=model,
        ANTHROPIC_DEFAULT_SONNET_MODEL=model,ANTHROPIC_DEFAULT_HAIKU_MODEL=model,CLAUDE_CODE_SUBAGENT_MODEL=model)
    return result

def profile_for(root,home,python,port=None,read_only_paths=None):
    profile=original_profile(root,home,python.parent.parent,port,read_only_paths)
    # Ordinary tests can create local TCP fixtures. External network remains
    # denied. The relay credential is still held only by the parent process.
    if port is not None:profile+='(allow network-outbound (remote tcp "localhost:*"))\n'
    return profile

def preflight(python,output):
    import socket,threading
    from isolation import bootstrap_temp_dirs
    records=[]
    with tempfile.TemporaryDirectory(prefix='dn2-pf-',dir='/private/tmp') as directory:
        base=Path(directory).resolve();root=base/'workspace';home=base/'home';tmp=base/'tmp'
        for p in [root,home/'.claude',tmp]:p.mkdir(parents=True)
        env=env_for(root,home,tmp,python)
        bootstrap_temp_dirs(root)
        profile=base/'sandbox.sb';profile.write_text(profile_for(root,home,python,12345))
        prefix=['sandbox-exec','-D','CLI_PID=999999','-f',str(profile)]
        cases={
          'heredoc': ['/bin/zsh','-df','-c',"python3 - <<'PY'\nfrom pathlib import Path\nimport os,tempfile\np=Path(tempfile.mkstemp()[1]);p.write_text('ok');assert p.read_text()=='ok'\nprint('HEREDOC_OK')\nPY"],
          'mktemp_default':['/bin/zsh','-df','-c','p=$(mktemp); test -f "$p"; echo OK > "$p"; cat "$p"; case "$p" in "$TMPDIR"*) ;; *) exit 9;; esac'],
          'mktemp_dir':['/bin/zsh','-df','-c','p=$(mktemp -d); test -d "$p"; echo OK > "$p/test"; cat "$p/test"'],
          'mktemp_native':['/bin/zsh','-df','-c','p=$(/usr/bin/mktemp -p "$TMPDIR"); echo OK > "$p"; cat "$p"'],
          'shell_cwd':['/bin/zsh','-df','-c','pwd -P >| "$CLAUDE_CODE_TMPDIR/claude-preflight-cwd"; cat "$CLAUDE_CODE_TMPDIR/claude-preflight-cwd"'],
          'test_subprocess':['/bin/zsh','-df','-c','python3 -c "import subprocess,sys;subprocess.run([sys.executable,\'-m\',\'pytest\',\'-q\',\'test_probe.py\'],check=True)"'],
          'git':['git','status','--porcelain'],
          'claude_native_no_model':['claude','--version']}
        (root/'test_probe.py').write_text('def test_normal():\n assert sum(range(5)) == 10\n')
        subprocess.run([str(native_git()),'init','-q'],cwd=root,check=True)
        for name,argv in cases.items():
            p=subprocess.run(prefix+argv,cwd=root,env=env,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=30)
            records.append({'name':name,'argv':argv,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
        with socket.socket() as listener:
            listener.bind(('127.0.0.1',0));listener.listen();port=listener.getsockname()[1]
            argv=[str(python),'-c','import socket,sys;s=socket.create_connection(("127.0.0.1",int(sys.argv[1])));s.close();print("LOCAL_TCP_OK")',str(port)]
            p=subprocess.run(prefix+argv,cwd=root,env=env,capture_output=True,text=True,timeout=15)
            records.append({'name':'ordinary_local_test_socket','exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
        # A previous answer remains inaccessible even with ordinary scratch enabled.
        with tempfile.TemporaryDirectory(prefix='dn2-old-',dir='/private/tmp') as sibling:
            target=Path(sibling)/'answer';target.write_text('previous answer')
            argv=[str(python),'-c','from pathlib import Path;import sys\ntry:Path(sys.argv[1]).read_text()\nexcept PermissionError: print("SIBLING_DENIED")\nelse:raise AssertionError("leak")',str(target)]
            p=subprocess.run(prefix+argv,cwd=root,env=env,capture_output=True,text=True,timeout=15)
            records.append({'name':'sibling_isolation','exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
        passed=all(r['exit_code']==0 for r in records)
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps({'passed':passed,'model_calls':0,'environment':env,'profile':profile.read_text(),'cases':records},indent=2)+'\n')
        if not passed:raise RuntimeError('Environment preflight failed; see saved evidence.')
        return records
