"""Offline integration and negative tests. No model/API calls."""
import argparse
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("dn", ROOT / "skills/deep-native/scripts/deep_native.py")
dn = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dn)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        (self.root / "app.py").write_text("VALUE = 1\n")
        (self.root / ".gitignore").write_text("__pycache__/\nignored/\n")
        self.configure([sys.executable, "-c", "assert 1 + 1 == 2"])

    def configure(self, argv, name="tests"):
        dn.atomic_json(self.root, dn.CONFIG, {"schema": 1, "checks": [{"name": name, "argv": argv}]})

    def invoke(self, *args):
        return dn.execute(dn.parser().parse_args(list(args)), self.root)

    def begin(self):
        return self.invoke("begin", "--goal", "Correct behavior", "--session", "s1")[0]

    def verified(self):
        self.begin()
        result, code = self.invoke("verify")
        self.assertEqual(code, 0, result)
        return result

    def finish(self):
        return self.invoke("finish", "--summary", "Fixed", "--risk", "No live model test")

    def test_happy_path(self):
        self.verified()
        result, code = self.finish()
        self.assertEqual(result["status"], "complete")
        self.assertEqual(code, 0)

    def test_finish_without_verification(self):
        self.begin()
        with self.assertRaises(dn.Error): self.finish()

    def test_failed_check_rejected(self):
        self.configure([sys.executable, "-c", "raise SystemExit(7)"])
        self.begin()
        result, code = self.invoke("verify")
        self.assertEqual((code, result["checks"][0]["exit_code"]), (1, 7))
        with self.assertRaises(dn.Error): self.finish()

    def test_timeout(self):
        self.configure([sys.executable, "-c", "import time; time.sleep(10)"])
        self.begin()
        result, code = self.invoke("verify", "--timeout", "0.05")
        self.assertEqual(code, 1)
        self.assertTrue(result["checks"][0]["timeout"])
        with self.assertRaises(dn.Error): self.finish()

    def test_missing_executable(self):
        self.configure(["deep-native-intentionally-missing-command"])
        self.begin()
        result, code = self.invoke("verify")
        self.assertEqual((code, result["checks"][0]["exit_code"]), (1, 127))

    def test_stale_source_rejected(self):
        self.verified()
        (self.root / "app.py").write_text("VALUE = 2\n")
        with self.assertRaises(dn.Error): self.finish()

    def test_new_untracked_file_rejected(self):
        self.verified()
        (self.root / "new.py").write_text("pass\n")
        with self.assertRaises(dn.Error): self.finish()

    def test_deleted_tracked_file_rejected(self):
        dn.git(self.root, "add", "app.py")
        self.verified()
        (self.root / "app.py").unlink()
        with self.assertRaises(dn.Error): self.finish()

    def test_executable_mode_change_rejected(self):
        self.verified()
        (self.root / "app.py").chmod(0o755)
        with self.assertRaises(dn.Error): self.finish()

    def test_symlink_target_is_hashed_not_followed(self):
        (self.root / "link").symlink_to("/does/not/exist")
        self.verified()
        (self.root / "link").unlink()
        (self.root / "link").symlink_to("/different/target")
        with self.assertRaises(dn.Error): self.finish()

    def test_ignored_file_is_documented_exclusion(self):
        self.verified()
        (self.root / "ignored").mkdir()
        (self.root / "ignored/cache").write_text("cache")
        self.finish()

    def test_tracked_ignored_file_is_included(self):
        (self.root / "ignored").mkdir()
        (self.root / "ignored/code").write_text("one")
        dn.git(self.root, "add", "-f", "ignored/code")
        self.verified()
        (self.root / "ignored/code").write_text("two")
        with self.assertRaises(dn.Error): self.finish()

    def test_checks_cannot_change_during_task(self):
        self.begin()
        with self.assertRaises(dn.Error):
            self.invoke("configure", "--name", "other", "--", "true")

    def test_direct_contract_edit_invalidates(self):
        self.verified()
        self.configure([sys.executable, "-c", "pass"])
        with self.assertRaises(dn.Error): self.finish()

    def test_mutating_check_is_not_success(self):
        self.configure([sys.executable, "-c", "from pathlib import Path; Path('app.py').write_text('changed')"])
        self.begin()
        result, code = self.invoke("verify")
        self.assertEqual(code, 1)
        self.assertNotEqual(result["before"], result["after"])

    def test_latest_failure_invalidates_previous_pass(self):
        (self.root / "ignored").mkdir()
        (self.root / "ignored/ok").write_text("yes")
        self.configure([sys.executable, "-c", "from pathlib import Path; assert Path('ignored/ok').exists()"])
        self.verified()
        (self.root / "ignored/ok").unlink()
        self.assertEqual(self.invoke("verify")[1], 1)
        with self.assertRaises(dn.Error): self.finish()

    def test_evidence_write_failure_does_not_reuse_success(self):
        self.verified()
        original = dn.atomic_json
        def fail_final(root, relative, value):
            if value.get("status") == "passed": raise OSError("injected disk failure")
            original(root, relative, value)
        with patch.object(dn, "atomic_json", side_effect=fail_final):
            with self.assertRaises(OSError): self.invoke("verify")
        with self.assertRaises(dn.Error): self.finish()

    def test_missing_evidence(self):
        self.verified()
        task = dn.state(self.root)
        (self.root / f".deep-native/attempts/{task['attempt']}.json").unlink()
        with self.assertRaises(dn.Error): self.finish()

    def test_wrong_task_evidence(self):
        self.verified()
        task = dn.state(self.root)
        path = f".deep-native/attempts/{task['attempt']}.json"
        evidence = dn.read_json(self.root / path)
        evidence["task_id"] = "another-task"
        dn.atomic_json(self.root, path, evidence)
        with self.assertRaises(dn.Error): self.finish()

    def test_missing_check_evidence(self):
        self.verified()
        task = dn.state(self.root)
        path = f".deep-native/attempts/{task['attempt']}.json"
        evidence = dn.read_json(self.root / path)
        evidence["checks"] = []
        dn.atomic_json(self.root, path, evidence)
        with self.assertRaises(dn.Error): self.finish()

    def test_all_checks_required(self):
        self.invoke("configure", "--name", "second", "--", sys.executable, "-c", "raise SystemExit(1)")
        self.begin()
        result, code = self.invoke("verify")
        self.assertEqual(len(result["checks"]), 2)
        self.assertEqual(code, 1)

    def test_no_shell_expansion(self):
        self.configure([sys.executable, "-c", "import sys; assert sys.argv[1] == '$(touch PWNED)'", "$(touch PWNED)"])
        self.verified()
        self.assertFalse((self.root / "PWNED").exists())

    def test_api_credentials_not_forwarded_or_logged(self):
        secret = "test-credential-do-not-persist-93482"
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": secret}):
            self.configure([sys.executable, "-c", "import os; assert 'DEEPSEEK_API_KEY' not in os.environ; print('not retained')"])
            result = self.verified()
            self.assertNotIn(secret, json.dumps(result))
            self.assertNotIn("stdout", result["checks"][0])

    def test_secret_in_text_rejected(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "private-example-credential-98475"}):
            with self.assertRaises(dn.Error): dn.safe_text("private-example-credential-98475")
        with self.assertRaises(dn.Error): dn.safe_text("sk-12345678901234567890")

    def test_doctor_does_not_show_custom_endpoint_or_key(self):
        with patch.dict(os.environ, {"ANTHROPIC_BASE_URL": "https://user:secret@example.test/token", "ANTHROPIC_AUTH_TOKEN": "fake-value"}):
            result = dn.doctor(self.root)
        self.assertTrue(result["credential_present"])
        self.assertEqual(result["live_api_test"], "NOT_RUN")
        self.assertNotIn("example.test", json.dumps(result))
        self.assertNotIn("fake-value", json.dumps(result))

    def test_checkpoint_restore(self):
        self.begin()
        self.invoke("checkpoint", "--note", "Found wrong boundary", "--next", "Add regression")
        output = dn.hook(self.root, {"hook_event_name": "SessionStart", "session_id": "s1", "source": "compact"})
        self.assertIn("Found wrong boundary", json.dumps(output))

    def test_stop_blocks_missing_verification(self):
        self.begin()
        result = dn.hook(self.root, {"hook_event_name": "Stop", "session_id": "s1"})
        self.assertEqual(result["decision"], "block")

    def test_stop_loop_escape_not_success(self):
        self.begin()
        result = dn.hook(self.root, {"hook_event_name": "Stop", "session_id": "s1", "stop_hook_active": True})
        self.assertIn("UNVERIFIED", result["systemMessage"])
        self.assertNotIn("decision", result)
        with self.assertRaises(dn.Error): self.finish()

    def test_other_session_not_blocked(self):
        self.begin()
        self.assertEqual(dn.hook(self.root, {"hook_event_name": "Stop", "session_id": "s2"}), {})

    def test_no_task_no_hook(self):
        self.assertEqual(dn.hook(self.root, {"hook_event_name": "Stop", "session_id": "s1"}), {})

    def test_verified_stop_allowed(self):
        self.verified()
        self.assertEqual(dn.hook(self.root, {"hook_event_name": "Stop", "session_id": "s1"}), {})

    def test_block_is_not_complete(self):
        self.begin()
        result, _ = self.invoke("block", "--reason", "Dependency unavailable")
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(dn.hook(self.root, {"hook_event_name": "Stop", "session_id": "s1"}), {})
        with self.assertRaises(dn.Error): self.finish()

    def test_adopt_session(self):
        self.begin()
        self.invoke("adopt", "--session", "s2")
        self.assertEqual(dn.state(self.root)["session"], "s2")

    def test_duplicate_begin_rejected(self):
        self.begin()
        with self.assertRaises(dn.Error): self.begin()

    def test_corrupt_state_not_replaced(self):
        dn.atomic_json(self.root, ".deep-native/state.json", {"broken": True})
        with self.assertRaises(dn.Error): self.begin()

    def test_invalid_hook_payload(self):
        with self.assertRaises(dn.Error): dn.hook(self.root, [])

    def test_invalid_hook_json_diagnostic(self):
        output = io.StringIO()
        with patch("sys.stdin", io.StringIO("{")), redirect_stdout(output):
            code = dn.main(["--project", str(self.root), "hook"])
        self.assertEqual(code, 0)
        self.assertIn("NOT certified", output.getvalue())

    def test_nan_timeout_rejected(self):
        self.begin()
        with self.assertRaises(dn.Error): self.invoke("verify", "--timeout", "nan")

    def test_nested_project_rejected(self):
        sub = self.root / "sub"; sub.mkdir()
        with self.assertRaises(dn.Error): dn.project(str(sub))

    def test_managed_symlink_rejected(self):
        (self.root / ".deep-native").symlink_to(self.root / "outside")
        with self.assertRaises(dn.Error): self.begin()

    def test_path_traversal_rejected(self):
        with self.assertRaises(dn.Error): dn.safe_path(self.root, "../outside")

    def test_nonblocking_lock(self):
        with dn.locked(self.root):
            with self.assertRaises(dn.Error):
                with dn.locked(self.root): pass

    def test_install_and_idempotence(self):
        first = dn.install(self.root, True)
        second = dn.install(self.root, True)
        self.assertEqual(first, second)
        settings = dn.read_json(self.root / ".claude/settings.local.json")
        self.assertEqual(len(settings["hooks"]["Stop"]), 1)

    def test_install_preserves_existing_settings(self):
        dn.atomic_json(self.root, ".claude/settings.local.json", {"permissions": {"deny": ["Bash(rm *)"]}, "hooks": {"Stop": [{"hooks": []}]}})
        dn.install(self.root, True)
        settings = dn.read_json(self.root / ".claude/settings.local.json")
        self.assertEqual(settings["permissions"]["deny"], ["Bash(rm *)"])
        self.assertEqual(len(settings["hooks"]["Stop"]), 2)

    def test_install_refuses_modified_skill(self):
        dn.install(self.root, False)
        (self.root / ".claude/skills/deep-native/SKILL.md").write_text("my custom skill")
        with self.assertRaises(dn.Error): dn.install(self.root, False)

    def test_install_rejects_symlink(self):
        (self.root / ".claude").symlink_to(self.root / "outside")
        with self.assertRaises(dn.Error): dn.install(self.root, False)

    def test_bad_settings_leave_skill_uninstalled(self):
        dn.atomic_json(self.root, ".claude/settings.local.json", {"hooks": {"Stop": 123}})
        with self.assertRaises(dn.Error): dn.install(self.root, True)
        self.assertFalse((self.root / ".claude/skills/deep-native/SKILL.md").exists())

    def test_invalid_config(self):
        for value in ({}, {"schema": 1, "checks": []}, {"schema": 1, "checks": [{"name": "t", "argv": "echo hi"}]}):
            with self.subTest(value=value):
                dn.atomic_json(self.root, dn.CONFIG, value)
                with self.assertRaises(dn.Error): self.begin()

    def test_duplicate_check_names(self):
        value = {"schema": 1, "checks": [{"name": "t", "argv": ["true"]}] * 2}
        dn.atomic_json(self.root, dn.CONFIG, value)
        with self.assertRaises(dn.Error): self.begin()

    def test_installed_hook_command_runs_in_path_with_spaces(self):
        import shlex
        work = self.root / "project with spaces"
        work.mkdir()
        subprocess.run(["git", "init", "-q", str(work)], check=True)
        dn.install(work, True)
        settings = dn.read_json(work / ".claude/settings.local.json")
        command = settings["hooks"]["Stop"][0]["hooks"][0]["command"]
        result = subprocess.run(shlex.split(command), input='{"hook_event_name":"Stop"}',
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {})

    def test_atomic_write_does_not_leave_temp_files(self):
        dn.atomic_json(self.root, ".deep-native/sample.json", {"ok": True})
        self.assertEqual(list((self.root / ".deep-native").glob(".write-*")), [])
        self.assertEqual((self.root / ".deep-native/sample.json").stat().st_mode & 0o777, 0o600)

    def test_head_change_invalidates_evidence(self):
        dn.git(self.root, "add", ".")
        dn.git(self.root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture")
        self.verified()
        dn.git(self.root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "--allow-empty", "-qm", "new head")
        with self.assertRaises(dn.Error): self.finish()

    def test_cli_error_exit_is_two(self):
        self.begin()
        with redirect_stderr(io.StringIO()):
            code = dn.main(["--project", str(self.root), "finish", "--summary", "x", "--risk", "y"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
