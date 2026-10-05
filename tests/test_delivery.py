import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("bench", ROOT / "evals/bench.py")
bench = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bench)
FIXED = '''def attempts(retries):
    if type(retries) is not int: raise TypeError()
    if retries < 0: raise ValueError()
    return retries + 1

def pages(items, size):
    if type(size) is not int: raise TypeError()
    if size <= 0: raise ValueError()
    return [items[i:i+size] for i in range(0,len(items),size)]

def merge(base, extra):
    return {**base, **extra}
'''


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_initial_fixture_fails_external_grader(self):
        work = self.root / "raw"
        bench.prepare(work, "raw")
        result = bench.grade(work)
        self.assertFalse(result["all_contract_tests_passed"])
        self.assertEqual(result["model_comparison"], "NOT_RUN")

    def test_scripted_reference_passes_external_grader(self):
        work = self.root / "raw"
        bench.prepare(work, "raw")
        (work / "solution.py").write_text(FIXED)
        self.assertTrue(bench.grade(work)["all_contract_tests_passed"])

    def test_all_arms_have_identical_initial_task(self):
        results = [bench.prepare(self.root / arm, arm) for arm in ("raw", "skill", "claude")]
        self.assertEqual(len({r["initial_sha256"] for r in results}), 1)
        self.assertEqual(len({r["task_sha256"] for r in results}), 1)
        self.assertTrue((self.root / "skill/.claude/skills/deep-native/SKILL.md").is_file())
        self.assertFalse((self.root / "raw/.claude").exists())

    def test_modified_visible_tests_do_not_replace_grader(self):
        work = self.root / "raw"
        bench.prepare(work, "raw")
        (work / "test_visible.py").write_text("# removed all tests\n")
        self.assertFalse(bench.grade(work)["all_contract_tests_passed"])

    def test_workspace_not_overwritten(self):
        work = self.root / "raw"
        bench.prepare(work, "raw")
        with self.assertRaises(ValueError): bench.prepare(work, "raw")

    def test_symlinked_submission_rejected(self):
        work = self.root / "raw"
        bench.prepare(work, "raw")
        (work / "solution.py").unlink()
        (work / "solution.py").symlink_to("test_visible.py")
        with self.assertRaises(ValueError): bench.grade(work)

    def test_skill_is_small_and_has_no_permission_bypass(self):
        skill = (ROOT / "skills/deep-native/SKILL.md").read_text()
        self.assertTrue(skill.startswith("---\nname: deep-native\n"))
        self.assertLess(len(skill.splitlines()), 200)
        self.assertNotIn("allowed-tools:", skill)
        self.assertNotIn("dangerously-skip-permissions", skill)
        self.assertIn("${CLAUDE_SKILL_DIR}", skill)

    def test_grader_does_not_export_arbitrary_output(self):
        work = self.root / "raw"
        bench.prepare(work, "raw")
        (work / "solution.py").write_text("print('PRIVATE_OUTPUT_184209')\n" + FIXED)
        self.assertNotIn("PRIVATE_OUTPUT_184209", json.dumps(bench.grade(work)))


if __name__ == "__main__": unittest.main()
