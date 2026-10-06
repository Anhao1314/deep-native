"""Real offline subprocess and Seatbelt checks; no Claude or provider calls."""
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1] / 'evals/benchmark-v1'
sys.path.insert(0, str(BENCH))
from isolation import ProcessOwner, claude_task_tree, sandbox_profile


def running(pid):
    result = subprocess.run(['ps', '-p', str(pid), '-o', 'stat='],
                            capture_output=True, text=True).stdout.strip()
    return bool(result and not result.startswith('Z'))


class ProcessOwnershipTests(unittest.TestCase):
    def exercise(self, exit_parent):
        code = ('import subprocess,sys,time; '
                'p=subprocess.Popen([sys.executable,"-B","-c","import time;time.sleep(30)"],'
                'start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); '
                'print(p.pid,flush=True); time.sleep(' + ('.5' if exit_parent else '30') + ')')
        proc = subprocess.Popen([sys.executable, '-B', '-c', code],
                                stdout=subprocess.PIPE, text=True, start_new_session=True)
        owner = ProcessOwner(proc)
        child = int(proc.stdout.readline().strip())
        try:
            owner.update()
            self.assertIn(child, owner.owned)
            if exit_parent:
                proc.wait(timeout=5)
                self.assertEqual(proc.returncode, 0)
            report = owner.cleanup()
            proc.wait(timeout=5)
            deadline = time.monotonic() + 3
            while running(child) and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertFalse(running(child))
            self.assertIn(child, report['signaled_pids'])
        finally:
            owner.cleanup()
            if running(child):
                os.kill(child, signal.SIGKILL)
            proc.stdout.close()

    def test_live_launcher_detached_descendant(self):
        self.exercise(False)

    def test_exited_launcher_retains_detached_descendant(self):
        self.exercise(True)

    def test_reused_pid_is_never_signaled(self):
        proc = type('Proc', (), {'pid': 70001, 'poll': lambda self: 0})()
        with patch('isolation._process_snapshot', return_value={}):
            owner = ProcessOwner(proc)
        owner.owned[70002] = 'old-start-identity'
        reused = {70002: {'ppid': 1, 'identity': 'new-start-identity'}}
        with patch('isolation._process_snapshot', return_value=reused), \
             patch('isolation.os.kill') as kill:
            owner.cleanup()
        kill.assert_not_called()


class AgentEnvironmentTests(unittest.TestCase):
    def test_runtime_git_uses_linux_path_fallback(self):
        from harness import runtime_git
        with patch('harness.platform.system', return_value='Linux'), \
             patch('harness.shutil.which', return_value='/fixture/git'):
            self.assertEqual(runtime_git(), Path('/fixture/git'))

    def test_native_scratch_is_scoped_to_each_run(self):
        from harness import agent_env
        relay = type('Relay', (), {'url': 'http://127.0.0.1:12345'})()
        environments = []
        with patch('harness.shutil.which', return_value='/tools/claude'):
            for name in ['run-a', 'run-b']:
                base = Path('/private/tmp') / name
                environments.append(agent_env(base / 'home', base / 'tmp',
                                              Path(sys.executable), relay, 'offline-model'))
        self.assertNotEqual(environments[0]['CLAUDE_CODE_TMPDIR'],
                            environments[1]['CLAUDE_CODE_TMPDIR'])
        for env in environments:
            self.assertEqual(env['CLAUDE_CODE_TMPDIR'], env['TMPDIR'])
            self.assertEqual(Path(env['CLAUDE_CODE_TMPDIR']).parent,
                             Path(env['HOME']).parent)


@unittest.skipUnless(sys.platform == 'darwin' and shutil.which('sandbox-exec'),
                     'Seatbelt is only available on macOS')
class SandboxTests(unittest.TestCase):
    def test_native_git_status_has_no_shim_cache_warnings(self):
        from harness import agent_env, runtime_git
        git = runtime_git()
        if git != Path('/Library/Developer/CommandLineTools/usr/bin/git'):
            self.skipTest('Native macOS Command Line Tools Git is unavailable')
        with tempfile.TemporaryDirectory(prefix='dn-live-', dir='/private/tmp') as current:
            base = Path(current).resolve(); root = base / 'workspace'; home = base / 'home'
            tmp = base / 'tmp'
            root.mkdir(); home.mkdir(); tmp.mkdir()
            subprocess.run([str(git), 'init', '-q', str(root)], check=True, capture_output=True)
            relay = type('Relay', (), {'url': 'http://127.0.0.1:12345'})()
            with patch('harness.shutil.which', return_value='/tools/claude'):
                env = agent_env(home, tmp, Path(sys.executable), relay, 'offline-model')
            profile = base / 'sandbox.sb'
            profile.write_text(sandbox_profile(root, home, Path('/usr/bin'), None))
            expected = subprocess.run([str(git), '--version'], check=True,
                                      capture_output=True, text=True).stdout.strip()
            script = ('import shutil,subprocess,sys; '
                      'assert shutil.which("git")==sys.argv[1]; '
                      'version=subprocess.run(["git","--version"],check=True,capture_output=True,text=True); '
                      'assert version.stdout.strip()==sys.argv[2]; assert not version.stderr,version.stderr; '
                      'status=subprocess.run(["git","status","--porcelain"],check=True,capture_output=True,text=True); '
                      'assert not status.stderr,status.stderr; assert not status.stdout,status.stdout')
            argv = ['sandbox-exec', '-D', 'CLI_PID=999999', '-f', str(profile),
                    str(Path(sys.executable).resolve()), '-B', '-c', script, str(git), expected]
            result = subprocess.run(argv, cwd=root, env=env, capture_output=True,
                                    text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(result.stderr, result.stderr)

    def test_native_cwd_receipt_tasks_and_socket_stay_in_run(self):
        from harness import agent_env
        with tempfile.TemporaryDirectory(prefix='dn-live-', dir='/private/tmp') as current, \
             tempfile.TemporaryDirectory(prefix='dn-live-', dir='/private/tmp') as sibling:
            base = Path(current).resolve(); root = base / 'workspace'; home = base / 'home'
            tmp = base / 'tmp'
            root.mkdir(); home.mkdir(); tmp.mkdir()
            previous = Path(sibling) / 'claude-offline-cwd'; previous.write_text('other run')
            relay = type('Relay', (), {'url': 'http://127.0.0.1:12345'})()
            with patch('harness.shutil.which', return_value='/tools/claude'):
                env = agent_env(home, tmp, Path(sys.executable), relay, 'offline-model')
            profile = base / 'sandbox.sb'
            profile.write_text(sandbox_profile(root, home, Path('/usr/bin'), None))
            script = ('import os,pathlib,socket,subprocess,sys; '
                      'tmp=pathlib.Path(os.environ["CLAUDE_CODE_TMPDIR"]); '
                      'subprocess.run(["/bin/zsh","-df","-c",'
                      '\'pwd -P >| "$CLAUDE_CODE_TMPDIR/claude-offline-cwd"\'],check=True); '
                      'assert (tmp/"claude-offline-cwd").read_text().strip()==str(pathlib.Path.cwd()); '
                      'task=tmp/("claude-"+str(os.getuid()))/"offline-cwd"/"tasks"; '
                      'task.mkdir(parents=True); (task/"output.txt").write_text("ok"); '
                      'ipc=tmp/"cc-socks"; ipc.mkdir(); '
                      '\nwith socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as server:\n'
                      ' server.bind(str(ipc/"offline.sock"))\n'
                      'try: pathlib.Path(sys.argv[1]).read_text()\n'
                      'except PermissionError: pass\n'
                      'else: raise AssertionError("other run scratch readable")\n')
            argv = ['sandbox-exec', '-D', 'CLI_PID=999999', '-f', str(profile),
                    str(Path(sys.executable).resolve()), '-B', '-c', script, str(previous)]
            result = subprocess.run(argv, cwd=root, env=env, capture_output=True,
                                    text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn('operation not permitted', result.stderr.lower())
            self.assertEqual((tmp / 'claude-offline-cwd').read_text().strip(), str(root))

    def test_literal_evaluator_exception_and_offline_subprocess(self):
        with tempfile.TemporaryDirectory(prefix='dn-grade-', dir='/private/tmp') as current, \
             tempfile.TemporaryDirectory(prefix='dn-evaluator-', dir='/private/tmp') as evaluator:
            base = Path(current).resolve(); root = base / 'workspace'; home = base / 'home'
            root.mkdir(); home.mkdir(); (base / 'tmp').mkdir()
            acceptance = Path(evaluator) / 'acceptance.py'; acceptance.write_text('approved evaluator')
            reference = Path(evaluator) / 'reference.py'; reference.write_text('hidden answer')
            profile = base / 'sandbox.sb'
            profile.write_text(sandbox_profile(root, home, Path('/usr/bin'), None,
                                               read_only_paths=[acceptance, BENCH / 'acceptance.py']))
            # The recorded deployment repository is under ~/Documents. GitHub's
            # /Users/runner/work checkout is outside this scoped read policy;
            # always enforce the temp sibling guard, and check the real reference
            # only when its actual location is inside a denied tree.
            denied_roots = [Path.home().resolve() / 'Documents', Path('/private/tmp'),
                            Path('/private/var/tmp'), Path(tempfile.gettempdir()).resolve()]
            real_reference = (BENCH / 'reference.py').resolve()
            guard_real_reference = any(path == real_reference or path in real_reference.parents
                                       for path in denied_roots)
            with socket.socket() as listener:
                listener.bind(('127.0.0.1', 0)); listener.listen()
                port = listener.getsockname()[1]
                script = ('import errno,pathlib,socket,subprocess,sys; '
                          'acceptance,reference=map(pathlib.Path,sys.argv[1:3]); '
                          'assert acceptance.read_text()=="approved evaluator"; '
                          'assert pathlib.Path(sys.argv[4]).read_text(); '
                          'checks=[(reference,"read"),(acceptance,"write")]; '
                          '\nif sys.argv[6]=="1": checks.append((pathlib.Path(sys.argv[5]),"read"))\n'
                          'for path,op in checks:\n'
                          ' try:\n'
                          '  path.read_text() if op=="read" else path.write_text("forbidden")\n'
                          ' except PermissionError: pass\n'
                          ' else: raise AssertionError(str(path)+" "+op+" permitted")\n'
                          'with socket.socket() as client:\n'
                          ' try: client.connect(("127.0.0.1",int(sys.argv[3])))\n'
                          ' except OSError as exc: assert exc.errno in (errno.EPERM,errno.EACCES),exc\n'
                          ' else: raise AssertionError("offline grader network permitted")\n'
                          'subprocess.run([sys.executable,"-B","-c",'
                          '"from pathlib import Path;Path(\\\"child.txt\\\").write_text(\\\"ok\\\")"],check=True)\n')
                argv = ['sandbox-exec', '-D', 'CLI_PID=999999', '-f', str(profile),
                        str(Path(sys.executable).resolve()), '-B', '-c', script, str(acceptance),
                        str(reference), str(port), str(BENCH / 'acceptance.py'),
                        str(real_reference), '1' if guard_real_reference else '0']
                result = subprocess.run(argv, cwd=root, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((root / 'child.txt').read_text(), 'ok')
            self.assertEqual(acceptance.read_text(), 'approved evaluator')

    def test_sibling_answers_and_outside_writes_denied(self):
        # Use actual benchmark-shaped paths. Both directories disappear afterward.
        with tempfile.TemporaryDirectory(prefix='dn-live-', dir='/private/tmp') as current, \
             tempfile.TemporaryDirectory(prefix='dn-live-', dir='/private/tmp') as sibling:
            base = Path(current).resolve(); root = base / 'workspace'; home = base / 'home'
            root.mkdir(); home.mkdir()
            answer = Path(sibling) / 'answer.py'; answer.write_text('previous solution')
            profile = base / 'sandbox.sb'
            # /usr/bin is a harmless, narrow dependency exception for this test.
            profile.write_text(sandbox_profile(root, home, Path('/usr/bin'), 12345))
            task_tree = claude_task_tree(root)
            previous_task = task_tree.parent / ('previous-' + base.name)
            previous_task.mkdir(parents=True)
            old_output = previous_task / 'answer.txt'; old_output.write_text('old tool output')
            try:
                own_output = task_tree / 'tasks/output.txt'
                script = ('import pathlib,sys; '
                          'root,sibling,old,own=map(pathlib.Path,sys.argv[1:]); '
                          '(root/"allowed.txt").write_text("ok"); '
                          'own.parent.mkdir(parents=True,exist_ok=True); own.write_text("ok"); '
                          '\nfor path,operation in [(sibling,"read"),(old,"read"),(sibling,"write")]:\n'
                          ' try:\n'
                          '  path.read_text() if operation=="read" else path.write_text("forbidden")\n'
                          ' except PermissionError: pass\n'
                          ' else: raise AssertionError(str(path)+" "+operation+" permitted")\n')
                argv = ['sandbox-exec', '-D', 'CLI_PID=999999', '-f', str(profile),
                        str(Path(sys.executable).resolve()), '-B', '-c', script, str(root), str(answer),
                        str(old_output), str(own_output)]
                result = subprocess.run(argv, cwd=root, capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual((root / 'allowed.txt').read_text(), 'ok')
                self.assertEqual(answer.read_text(), 'previous solution')
            finally:
                shutil.rmtree(task_tree, ignore_errors=True)
                shutil.rmtree(previous_task, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
