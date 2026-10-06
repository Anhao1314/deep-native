import ast,json
from pathlib import Path

UPSTREAM={'url':'https://github.com/tkem/cachetools.git','commit':'9976f1a8076631560f49c5b0dfda7e4d00ee0a4a'}
ARMS={'A':None,'B':'fda3dd010e7de8f8c1ee1953e006e577464aa3d6','C':'824c3009e465a1748250f5ed8589e096237dcb08'}
BUDGET={'assistant_attempts':48,'wall_seconds':900,'phase1_max_attempts':28,'phase1_max_seconds':540}
COMMON=''' Work only on the stated functionality. Do not change upstream tests, benchmark_tests.py, benchmark_phase.json, or the check receipt implementation. You may add agent_tests/ and documentation. Do not hard-code answers, skip tests, or weaken acceptance. The project is imported from src/ (PYTHONPATH is already set). Use python3 run_checks.py for meaningful task and upstream verification; report checks actually executed. Scratch paths must use the writable per-run $TMPDIR rather than global /tmp. End your final response with STATUS: DONE or STATUS: BLOCKED.'''
TASKS=[
 {'id':'D1','family':'hard_root_cause','files':['src/cachetools/_cached.py','src/cachetools/_cachedmethod.py'],
 'prompt':'''Investigate a regression in cachetools: while one cached function or method computation is held, callers for a different key can stall, including already cached values. The operator suspects LRU eviction or the user function holding the cache lock; treat this as an unconfirmed hypothesis. Restore independent-key progress for cached and cachedmethod, with info both enabled and disabled. Preserve same-key stampede suppression, cache hits/misses, exception cleanup and existing public behavior. Reproduce with discriminating evidence and add regression protection.'''+COMMON},
 {'id':'E1','family':'environment_classification','files':['run_checks.py'],
 'prompt':'''The delivered check command python3 run_checks.py fails before the cache checks can finish. The operator suspects cache serialization. Diagnose the failure category and get the checks running reliably. Existing cache product behavior must stay unchanged; do not modify src/cachetools or upstream tests. You may adapt the launcher/invocation. The .fixture-readonly directory is an intentionally non-writable fixture: do not chmod, delete or write it. Capture the actual check outcome and explain the cause.'''+COMMON},
 {'id':'F1','family':'fresh_verification','files':['src/cachetools/__init__.py'],
 'prompt':'''Add Cache.pop_many(keys): remove present keys in first-seen iterable order, return a list of (key,value) pairs, ignore missing keys and duplicate requests, preserve value identity and correct currsize, and never invoke __missing__ for absent keys. Implement and run the phase-one checks now. A subsequent message will extend this acceptance contract before delivery; do not anticipate unrequested APIs.'''+COMMON,
 'continuation':'''The acceptance contract has now changed. Extend Cache.pop_many with keyword-only strict=False. Default behavior stays unchanged. With strict=True, materialize and validate all requested keys before removal; any missing key raises KeyError and any iterator failure leaves the cache completely unchanged. Duplicate existing keys still remove once. Complete the updated task and report the actual final checks.'''+COMMON},
 {'id':'R1','family':'progress_checkpoint_recovery','files':['src/cachetools/__init__.py'],
 'prompt':'''This cachetools task has two deliverables and the executor may interrupt it. First implement Cache.snapshot(): return an immutable tuple of (key,value) pairs in current insertion order, with shallow value identity, no mutation and correct existing size accounting. Verify this first milestone, then save substantive progress notes containing confirmed facts, changed files, checks and the concrete next action, using the available progress mechanism (use PROGRESS.md if no checkpoint mechanism is installed). Do not implement restore yet. The next phase will add Cache.restore(snapshot): atomically replace contents after validating all records, sizes and duplicates. This two-part work is one task; preserve progress for continuation rather than claiming the whole task is already complete.'''+COMMON,
 'continuation':'''Continue the interrupted cachetools task. Complete Cache.restore(snapshot) for base Cache instances: accept an iterable of tuple/list records of exactly two elements; reject duplicate keys, unhashable keys, malformed records, negative/oversized values or total size exceeding maxsize. If iteration, hashing or getsizeof fails, preserve all old contents and currsize. On success replace all entries in input order, preserve value identity, set correct currsize and return None. Existing snapshot behavior must remain correct. Use saved progress and inspect the actual source; finish with real checks and remaining limitations.'''+COMMON}
]

def manifest():return {'schema':1,'arms':ARMS,'repository':UPSTREAM,'budget':BUDGET,'seed':20261007,'tasks':TASKS,
 'activation':'Use the installed deep-native skill for this task.','planned_runs':12,
 'milestone_definition':'R1 phase1 satisfies snapshot/identity-size milestones (2 of 4); restore/atomic-invalid milestones remain incomplete.',
 'judgment':'CONTINUE only for a clear C mechanism win without strict quality regression and with explainable overhead; ANALYZE for mixed tied quality; STOP for a C strict-quality loss or unexplained added work without mechanism wins.'}

CHECK_RECEIPT='''import hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def fingerprint():
 files=sorted(list((ROOT/'src/cachetools').rglob('*.py'))+list((ROOT/'agent_tests').rglob('*.py'))+[ROOT/'benchmark_tests.py',ROOT/'benchmark_phase.json',ROOT/'run_checks.py',ROOT/'check_receipt.py'])
 return hashlib.sha256(b''.join(str(p.relative_to(ROOT)).encode()+b'\\0'+p.read_bytes()+b'\\0' for p in files)).hexdigest()
def execute():
 sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT))
 import benchmark_tests
 os.environ['PYTHONPATH']=str(ROOT/'src');os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
 phase=json.loads((ROOT/'benchmark_phase.json').read_text());before=fingerprint();started=time.time()
 ok,n=benchmark_tests.run(phase['task'],phase['phase'])
 upstream=subprocess.run([sys.executable,'-m','pytest','-q','tests'],cwd=ROOT)
 extra=subprocess.run([sys.executable,'-m','pytest','-q','agent_tests'],cwd=ROOT) if (ROOT/'agent_tests').exists() else None
 passed=ok and upstream.returncode==0 and (extra is None or extra.returncode==0)
 after=fingerprint();record={'task':phase['task'],'phase':phase['phase'],'task_tests':n,'passed':passed and before==after,'source_before':before,'source_after':after,'started_epoch':started,'ended_epoch':time.time(),'pid':os.getpid(),'upstream_exit':upstream.returncode,'extra_exit':extra.returncode if extra else None}
 receipts=ROOT/'.experiment';receipts.mkdir(exist_ok=True)
 with (receipts/'checks.jsonl').open('a') as f:f.write(json.dumps(record)+'\\n')
 print('TASK_CHECK_RESULT '+json.dumps(record),flush=True)
 return 0 if record['passed'] else 1
'''

def seed(root,task,here):
    if task['id']=='D1':
        for name,a,b in [('_cached.py','lambda: k not in pending','lambda: not pending'),('_cachedmethod.py','lambda: key not in self.__pending','lambda: not self.__pending'),('_cachedmethod.py','lambda: k not in pending','lambda: not pending')]:
            p=root/'src/cachetools'/name;s=p.read_text();assert s.count(a)==(2 if name=='_cached.py' else 1);s=s.replace(a,b);p.write_text(s)
    (root/'benchmark_tests.py').write_text(visible_tests(here,task['id'],1))
    (root/'benchmark_phase.json').write_text(json.dumps({'task':task['id'],'phase':1})+'\n')
    (root/'check_receipt.py').write_text(CHECK_RECEIPT)
    if task['id']=='E1':
        d=root/'.fixture-readonly';d.mkdir();(d/'README').write_text('Fixture: preserve directory permissions.\n')
        (root/'run_checks.py').write_text("from pathlib import Path\nimport os,tempfile\nfrom check_receipt import execute\nroot=Path(__file__).resolve().parent\nwith tempfile.TemporaryDirectory(dir=os.environ.get('CHECK_TMPDIR',str(root/'.fixture-readonly'))) as d:\n Path(d,'probe').write_text('environment probe')\n raise SystemExit(execute())\n")
    else:(root/'run_checks.py').write_text('from check_receipt import execute\nraise SystemExit(execute())\n')

def visible_tests(here,task,phase):
    names={'D1':['DebugTests'],'E1':['EnvironmentTests'],'F1':['FreshStageOne'],'R1':['RecoveryStageOne']}[task]
    if phase==2 and task in ['F1','R1']:names=names+[{'F1':'FreshStageTwo','R1':'RecoveryStageTwo'}[task]]
    tree=ast.parse((here/'task_tests.py').read_text())
    nodes=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.ClassDef) and n.name in names]
    text=ast.unparse(ast.Module(body=nodes,type_ignores=[]))+'\n'
    text+=f'''def run(task,phase):
    suite=unittest.defaultTestLoader.loadTestsFromTestCase({names[-1]})
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    return result.wasSuccessful(),result.testsRun
'''
    return text

def reference(root,task,phase=2):
    p=root/'src/cachetools/__init__.py'
    if task['id']=='D1':
        for name,a,b in [('_cached.py','lambda: not pending','lambda: k not in pending'),('_cachedmethod.py','lambda: not self.__pending','lambda: key not in self.__pending'),('_cachedmethod.py','lambda: not pending','lambda: k not in pending')]:
            f=root/'src/cachetools'/name;f.write_text(f.read_text().replace(a,b))
    if task['id']=='E1':
        f=root/'run_checks.py';f.write_text(f.read_text().replace("os.environ.get('CHECK_TMPDIR',str(root/'.fixture-readonly'))","os.environ['TMPDIR']"))
    if task['id']=='F1':
        method='''    def pop_many(self, keys, *, strict=False):
        keys = list(keys) if strict else keys
        if strict:
            for key in keys:
                if key not in self: raise KeyError(key)
        result = []
        for key in keys:
            if key in self: result.append((key, self.pop(key)))
        return result

'''
        p.write_text(p.read_text().replace('    def __delitem__(self, key):',method+'    def __delitem__(self, key):',1))
    if task['id']=='R1':
        method='''    def snapshot(self):
        return tuple(self.items())

'''
        if phase==2:method+='''    def restore(self, snapshot):
        other = Cache(self.maxsize, getsizeof=self.getsizeof)
        for record in snapshot:
            if not isinstance(record, (tuple, list)) or len(record) != 2: raise ValueError('invalid record')
            key, value = record
            if key in other: raise ValueError('duplicate')
            size = self.getsizeof(value)
            if size < 0 or other.currsize + size > self.maxsize: raise ValueError('oversized')
            other[key] = value
        self.__data = other.__data
        self.__size = other.__size
        self.__currsize = other.__currsize
        return None

'''
        p.write_text(p.read_text().replace('    def __delitem__(self, key):',method+'    def __delitem__(self, key):',1))
