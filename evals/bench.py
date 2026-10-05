#!/usr/bin/env python3
"""Prepare equal coding fixtures and grade submitted patches, without model calls."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
INITIAL = '''def attempts(retries):
    return max(1, retries)

def pages(items, size):
    return [items[i:i+size] for i in range(0, len(items)-1, size)]

def merge(base, extra):
    base.update(extra)
    return base
'''
TASK = '''# Coding task

Repair `solution.py` without changing the public function signatures.
- `attempts(retries)` returns one initial attempt plus retries. Accept only Python
  ints (not bools), reject negatives with ValueError and other types with TypeError.
- `pages(items, size)` accepts a list and a strictly positive int size (not bool).
  Return every item exactly once in order in lists of at most size items. Reject
  nonpositive sizes with ValueError and other size types with TypeError.
- `merge(base, extra)` shallow-merges two dicts, with extra winning conflicts,
  without mutating either input. Do not add dependencies or change other files.

Investigate, implement, and report what you verified and what remains untested.
'''
GRADER = '''import unittest
from solution import attempts, pages, merge
class Contract(unittest.TestCase):
    def test_attempts_zero(self): self.assertEqual(attempts(0), 1)
    def test_attempts_many(self): self.assertEqual(attempts(4), 5)
    def test_attempts_negative(self):
        with self.assertRaises(ValueError): attempts(-1)
    def test_attempts_type(self):
        for value in [True, 1.5, "1", None]:
            with self.subTest(value=value):
                with self.assertRaises(TypeError): attempts(value)
    def test_pages_single(self): self.assertEqual(pages([1], 2), [[1]])
    def test_pages_tail(self): self.assertEqual(pages([1,2,3,4,5], 2), [[1,2],[3,4],[5]])
    def test_pages_empty(self): self.assertEqual(pages([], 2), [])
    def test_pages_bad_size(self):
        for value in [0, -1]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError): pages([1,2], value)
    def test_pages_bad_type(self):
        for value in [True, 1.5, "2", None]:
            with self.subTest(value=value):
                with self.assertRaises(TypeError): pages([1,2], value)
    def test_merge_result(self): self.assertEqual(merge({"a":1}, {"a":2,"b":3}), {"a":2,"b":3})
    def test_merge_preserves_inputs(self):
        a,b = {"a":1}, {"b":2}
        out = merge(a,b)
        self.assertEqual(a, {"a":1}); self.assertEqual(b, {"b":2})
        self.assertIsNot(out,a); self.assertIsNot(out,b)
    def test_merge_empty_copy(self):
        a = {}; self.assertIsNot(merge(a,{}), a)
if __name__ == "__main__": unittest.main()
'''
VISIBLE = '''import unittest
from solution import attempts, pages, merge
class Smoke(unittest.TestCase):
    def test_zero(self): self.assertEqual(attempts(0), 1)
    def test_even_pages(self): self.assertEqual(pages([1,2], 1), [[1],[2]])
    def test_merge(self): self.assertEqual(merge({}, {"a":1}), {"a":1})
'''


def prepare(path: Path, arm: str):
    if path.exists(): raise ValueError("Use a fresh, nonexistent workspace.")
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    for name, text in {"solution.py": INITIAL, "test_visible.py": VISIBLE,
                       "TASK.md": TASK, ".gitignore": ".deep-native/\n__pycache__/\n.claude/settings.local.json\n"}.items():
        (path / name).write_text(text)
    if arm == "skill":
        subprocess.run([sys.executable, str(ROOT / "deep_native.py"), "--project", str(path), "install"], check=True, stdout=subprocess.DEVNULL)
    # Labels live outside the agent workspace. They are self-reported, not authentication.
    manifest = {"schema": 1, "arm": arm, "initial_sha256": hashlib.sha256(INITIAL.encode()).hexdigest(),
                "task_sha256": hashlib.sha256(TASK.encode()).hexdigest(), "live_model_run": "NOT_RUN"}
    path.with_suffix(path.suffix + ".manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def grade(path: Path):
    candidate = path / "solution.py"
    if candidate.is_symlink() or not candidate.is_file() or candidate.stat().st_size > 100_000:
        raise ValueError("Expected a regular solution.py smaller than 100 KB.")
    payload = candidate.read_bytes()
    # Runs only the submitted source and the external grader in a new directory.
    # This is filesystem separation, NOT a security sandbox for malicious patches.
    with tempfile.TemporaryDirectory(prefix="deep-native-grade-") as tmp:
        work = Path(tmp)
        (work / "solution.py").write_bytes(payload)
        (work / "test_contract.py").write_text(GRADER)
        env = {k: v for k, v in os.environ.items() if k in {"PATH", "LANG", "LC_ALL", "TMPDIR"}}
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        with tempfile.TemporaryFile() as log:
            proc = subprocess.Popen([sys.executable, "-I", "-c",
                "import sys,unittest; sys.path.insert(0,'.'); s=unittest.defaultTestLoader.discover('.'); r=unittest.TextTestRunner().run(s); sys.exit(not r.wasSuccessful())"],
                cwd=work, env=env, stdout=log, stderr=log, start_new_session=True)
            timed_out = False
            try:
                code = proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                timed_out, code = True, 124
            finally:
                import signal
                try: os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError: pass
                proc.wait()
            log.seek(0)
            text = log.read(64_000).decode(errors="replace")
    # Do not export arbitrary candidate output: it might contain local data/secrets.
    return {"schema": 1, "kind": "EXTERNAL_PATCH_GRADER", "all_contract_tests_passed": code == 0,
            "exit_code": code, "timeout": timed_out, "contract_test_methods": 12,
            "candidate_sha256": hashlib.sha256(payload).hexdigest(),
            "grader_sha256": hashlib.sha256(GRADER.encode()).hexdigest(),
            "model_identity": "NOT_ATTESTED", "model_comparison": "NOT_RUN"}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare"); prep.add_argument("--workspace", type=Path, required=True)
    prep.add_argument("--arm", choices=["raw", "skill", "claude"], required=True)
    gra = sub.add_parser("grade"); gra.add_argument("--workspace", type=Path, required=True)
    args = p.parse_args()
    try:
        result = prepare(args.workspace.resolve(), args.arm) if args.command == "prepare" else grade(args.workspace.resolve())
        print(json.dumps(result, indent=2))
        sys.exit(0 if result.get("all_contract_tests_passed", True) else 1)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(2)
