import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "skills/deep-native/scripts/policy.py"
SPEC = importlib.util.spec_from_file_location("policy", POLICY)
policy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(policy)


class PolicyTests(unittest.TestCase):
    def test_fast_is_default_for_clear_local_work(self):
        result = policy.choose_mode(scope="local", uncertainty="clear")
        self.assertEqual(result["mode"], "fast")
        self.assertFalse(result["runtime_required"])

    def test_cross_file_routes_standard(self):
        self.assertEqual(policy.choose_mode(scope="cross-file", uncertainty="clear")["mode"], "standard")

    def test_uncertain_root_cause_routes_standard(self):
        self.assertEqual(policy.choose_mode(scope="local", uncertainty="uncertain")["mode"], "standard")

    def test_first_failure_routes_standard(self):
        self.assertEqual(policy.choose_mode(scope="local", uncertainty="clear", failures=1)["mode"], "standard")

    def test_second_failure_escalates_deep(self):
        result = policy.choose_mode(scope="local", uncertainty="clear", failures=2)
        self.assertEqual(result["mode"], "deep")
        self.assertTrue(result["runtime_required"])

    def test_deep_risk_signals(self):
        for kwargs in ({"scope": "repo-wide"}, {"interruption_risk": True},
                       {"long_running": True}, {"high_risk": True}):
            base = {"scope": "local", "uncertainty": "clear"}
            base.update(kwargs)
            with self.subTest(kwargs=kwargs):
                self.assertEqual(policy.choose_mode(**base)["mode"], "deep")

    def test_negative_failure_count_rejected(self):
        with self.assertRaises(policy.PolicyError):
            policy.choose_mode(scope="local", uncertainty="clear", failures=-1)

    def test_environment_failure_changes_invocation_before_product_code(self):
        result = policy.failure_action("environment")
        self.assertIn("invocation", result["action"])
        self.assertFalse(result["escalate_to_deep"])

    def test_repeated_failure_escalates(self):
        self.assertTrue(policy.failure_action("hypothesis", repeated=True)["escalate_to_deep"])

    def test_cli_json(self):
        proc = subprocess.run(
            [sys.executable, str(POLICY), "route", "--scope", "local", "--uncertainty", "clear"],
            text=True, capture_output=True, check=True,
        )
        self.assertEqual(json.loads(proc.stdout)["mode"], "fast")


if __name__ == "__main__":
    unittest.main()
