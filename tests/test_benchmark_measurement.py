"""Offline measurement checks; never substitute for live model runs."""
import sys
import tempfile
import unittest
from pathlib import Path

BENCH=Path(__file__).resolve().parents[1]/'evals/benchmark-v1'
sys.path.insert(0,str(BENCH))
import harness

class MeasurementTests(unittest.TestCase):
    def test_reading_test_sources_is_not_execution(self):
        for command in ['cat benchmark_tests.py benchmark_check.py','sed -n 1,40p benchmark_check.py',
                        'rg unittest benchmark_tests.py','echo "python3 benchmark_check.py"']:
            self.assertFalse(harness.verification_command(command),command)

    def test_actual_check_invocations_and_helper_subcommand(self):
        for command in ['python3 benchmark_check.py','/tools/python -m pytest -q tests',
                        'python3 .claude/skills/deep-native/scripts/deep_native.py --project "$PWD" verify --timeout 60',
                        'cat benchmark_tests.py; python3 -m unittest discover -s tests',
                        'python3 benchmark_check.py | tail -10']:
            self.assertTrue(harness.verification_command(command),command)
        self.assertFalse(harness.verification_command('python3 .claude/skills/deep-native/scripts/deep_native.py configure --name tests -- python3 -m unittest'))

    def test_failed_pipeline_and_zero_test_collection_not_green(self):
        for text in ['3 failed, 60 passed in 1.2s','FAILED (failures=1)','no tests ran in 0.1s','Ran 0 tests in 0.000s']:
            self.assertFalse(harness.result_success({'content':text,'is_error':False}),text)
        self.assertTrue(harness.result_success({'content':'77 passed in 0.10s','is_error':False}))

    def test_only_final_standalone_status_line_declares_completion(self):
        self.assertTrue(harness.completion_declaration('Tests passed.\nSTATUS: DONE\n'))
        self.assertFalse(harness.completion_declaration('STATUS: DONE\nSTATUS: BLOCKED'))
        self.assertIsNone(harness.completion_declaration('I will write STATUS: DONE when finished.'))
        self.assertIsNone(harness.completion_declaration('STATUS: DONE\nMore work remains.'))

    def test_exhausted_shared_budget_grants_no_extra_turn(self):
        budget={'assistant_turns':24,'wall_seconds':480}
        self.assertEqual(harness.remaining_budget(budget,[{'observed_assistant_messages':24,'duration_seconds':400}]),(0,80))
        self.assertEqual(harness.remaining_budget(budget,[{'observed_assistant_messages':18,'duration_seconds':200}]),(6,280))
        with self.assertRaises(ValueError):
            harness.live_session(None,None,None,None,None,None,None,None,None,80,0)

    def test_type_and_regression_test_edits_invalidate_source_fingerprint(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'more_itertools').mkdir();(root/'agent_tests').mkdir()
            (root/'more_itertools/more.py').write_text('def f(): return 1\n')
            initial=harness.source_fingerprint(root)
            (root/'more_itertools/more.pyi').write_text('def f() -> int: ...\n')
            typed=harness.source_fingerprint(root)
            self.assertNotEqual(initial,typed)
            (root/'agent_tests/test_f.py').write_text('def test_f(): assert 1\n')
            self.assertNotEqual(typed,harness.source_fingerprint(root))

if __name__=='__main__':unittest.main()
