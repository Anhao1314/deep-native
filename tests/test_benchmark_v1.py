"""Harness tests use real subprocesses and offline patches, never mock models."""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

BENCH=Path(__file__).resolve().parents[1]/'evals/benchmark-v1'
sys.path.insert(0,str(BENCH))
import harness
from analysis import aggregate, paired_summary, wilson
from fixtures import TASKS
from transport import provider_tokens

class BenchmarkTests(unittest.TestCase):
    def test_balanced_randomized_schedule(self):
        schedule=harness.make_schedule()
        self.assertEqual(len(schedule),60)
        self.assertEqual(schedule,harness.make_schedule())
        self.assertNotEqual(schedule,harness.make_schedule(7))
        for i in range(0,60,2):
            a,b=schedule[i:i+2]
            self.assertEqual((a['task_id'],a['repeat']),(b['task_id'],b['repeat']))
            self.assertEqual({a['condition'],b['condition']},{'A','B'})
        self.assertEqual(len({s['run_id'] for s in schedule}),60)

    def test_exact_prompt_one_source_for_arms(self):
        for task in TASKS:
            self.assertTrue(task['prompt'].endswith('\n'))
            self.assertNotIn('/deep-native',task['prompt'])

    def test_secret_env_is_allowlist(self):
        relay=type('R',(),{'url':'http://127.0.0.1:12345'})()
        # Pure environment construction; no Claude executable/model is used by CI.
        with patch('harness.shutil.which',return_value='/tools/claude'):
            env=harness.agent_env(Path('/tmp/home'),Path('/tmp/t'),Path(sys.executable),relay,'model')
        self.assertEqual(env['ANTHROPIC_AUTH_TOKEN'],'benchmark-local-relay')
        self.assertNotIn('GH_TOKEN',env)
        self.assertNotIn('PYTHONPATH',env)

    def test_provider_usage_is_not_estimated(self):
        calls=[{'path':'/v1/messages','complete':True,'usage':{'input_tokens':20,'output_tokens':3,'cache_read_input_tokens':10}}]
        self.assertEqual(provider_tokens(calls)['total_tokens'],33)
        calls[0]['complete']=False
        self.assertIsNone(provider_tokens(calls))
        self.assertIsNone(provider_tokens([]))

    def test_behavior_links_actual_tool_results(self):
        events=[{'message':{'content':[{'type':'tool_use','id':'a','name':'Read','input':{'file_path':'a.py'}},
                 {'type':'tool_use','id':'b','name':'Edit','input':{}},
                 {'type':'tool_use','id':'c','name':'Bash','input':{'command':'python3 benchmark_check.py'}}]}},
                 {'message':{'content':[{'type':'tool_result','tool_use_id':'c','is_error':True}]}},
                 {'message':{'content':[{'type':'tool_use','id':'d','name':'Bash','input':{'command':'python3 benchmark_check.py'}}]}},
                 {'message':{'content':[{'type':'tool_result','tool_use_id':'d','is_error':False}]}}]
        b=harness.behavior(events)
        self.assertTrue(b['inspection_before_edit'])
        self.assertFalse(b['reproduction_before_edit'])
        self.assertTrue(b['successful_verification'])
        self.assertTrue(b['continued_after_failed_verification'])

    def test_completion_denominators(self):
        def row(passed,done):
            return {'task_success':'PASS' if passed else 'FAIL','declared_done':done,'actually_valid':passed,
                    'duration_seconds':1,'tool_calls':0,'files_changed':[],'tokens':None}
        a=aggregate([row(True,True),row(False,True),row(True,None),row(False,False)])
        self.assertEqual(a['success_rate'],.5)
        self.assertEqual(a['verified_completion_rate'],.5)
        self.assertEqual(a['verified_completion_per_run'],.25)
        self.assertEqual(a['false_completions'],1)
        self.assertEqual(a['unknown_declaration'],1)

    def test_wilson_and_task_cluster_pairing(self):
        self.assertIsNone(wilson(0,0))
        lo,hi=wilson(5,10)
        self.assertLess(lo,.5);self.assertGreater(hi,.5)
        rows=[{'task_id':t,'repeat':1,'condition':a,'task_success':'PASS' if a=='B' else 'FAIL'} for t in ['T01','T02'] for a in ['A','B']]
        result=paired_summary(rows)
        self.assertEqual(result['mean_task_delta'],1)
        self.assertEqual(result['complete_pairs'],2)

    def test_freeze_detects_modification(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)
            for name in ['tasks.json','schedule.json']:(out/name).write_text('{}')
            harness.dump(out/'freeze.json',{'protocol_sha256':{},'tasks_sha256':harness.digest(b'{}'),'schedule_sha256':harness.digest(b'{}')})
            harness.verify_freeze(out)
            (out/'tasks.json').write_text('[]')
            with self.assertRaises(ValueError):harness.verify_freeze(out)

    @unittest.skipUnless(os.environ.get('DN_BENCHMARK_CACHE') and os.environ.get('DN_BENCHMARK_PYTHON'),'Set cache/python to run network-free fixture validation')
    def test_all_fixtures_fail_and_reference_repairs_pass(self):
        from reference import repair
        cache=Path(os.environ['DN_BENCHMARK_CACHE']);python=Path(os.environ['DN_BENCHMARK_PYTHON'])
        for task in TASKS:
            with self.subTest(task=task['id']),tempfile.TemporaryDirectory() as temp:
                root=Path(temp)/'repo'
                commit=harness.prepare(root,task,cache,python)
                before=harness.grade(root,task,python)
                self.assertFalse(before['pass'])
                repair(root,task)
                after=harness.grade(root,task,python)
                self.assertTrue(after['pass'],json.dumps(after))

if __name__=='__main__':unittest.main()
