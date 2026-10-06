#!/usr/bin/env python3
"""Deep Native: local, evidence-bound coding workflow. Python 3.10+, stdlib only."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import uuid

VERSION = "0.1.0"
STATE_DIR = ".deep-native"
CONFIG = ".deep-native.json"
MAX_JSON = 1_000_000


class Error(Exception):
    """An actionable error whose message is safe to display."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def redact(text: str) -> str:
    for key, value in os.environ.items():
        if re.search(r"KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL", key, re.I) and len(value) >= 4:
            text = text.replace(value, "[REDACTED]")
    return re.sub(r"\b(?:sk-|ghp_|github_pat_)[A-Za-z0-9_-]{8,}", "[REDACTED]", text)


def safe_text(text: str, limit: int = 4000) -> str:
    if not isinstance(text, str) or not text.strip() or len(text) > limit or "\x00" in text:
        raise Error("Expected nonempty text within the documented length limit.")
    if redact(text) != text:
        raise Error("Credential-like content rejected. Do not put secrets in task text or commands.")
    return text.strip()


def safe_path(root: Path, relative: str) -> Path:
    parts = Path(relative).parts
    if not parts or Path(relative).is_absolute() or ".." in parts:
        raise Error("Unsafe relative path.")
    path = root
    for part in parts:
        path = path / part
        if path.is_symlink():
            raise Error("Refusing a symlink in a managed path.")
    return path


def read_json(path: Path):
    if path.stat().st_size > MAX_JSON:
        raise Error("JSON file is too large.")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise Error("Invalid JSON; no successful result can be inferred.") from exc


def atomic_json(root: Path, relative: str, value) -> None:
    path = safe_path(root, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_path(root, relative)
    fd, tmp = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded(value))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        if os.name == "posix":
            dfd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(dfd)
            finally:
                os.close(dfd)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def git(root: Path, *args: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", "-c", "core.fsmonitor=false", "-C", str(root), *args],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Error("Git is unavailable or timed out.") from exc
    if result.returncode:
        raise Error("Git command failed. Use a trusted Git working tree.")
    return result.stdout


def project(path: str) -> Path:
    root = Path(path).expanduser().resolve()
    if not root.is_dir():
        raise Error("Project directory does not exist.")
    actual = Path(os.fsdecode(git(root, "rev-parse", "--show-toplevel")).strip()).resolve()
    if actual != root:
        raise Error("--project must be the Git working-tree root, not a subdirectory.")
    return root


@contextlib.contextmanager
def locked(root: Path):
    if os.name != "posix":
        raise Error("Runtime locking currently supports macOS/Linux only; use WSL on Windows.")
    import fcntl
    directory = safe_path(root, STATE_DIR)
    directory.mkdir(exist_ok=True)
    path = safe_path(root, f"{STATE_DIR}/lock")
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise Error("Another Deep Native operation owns this workspace. Retry after it ends.") from exc
        yield
    finally:
        os.close(fd)


def config(root: Path):
    value = read_json(safe_path(root, CONFIG))
    if not isinstance(value, dict) or value.get("schema") != 1:
        raise Error("Unsupported check configuration schema.")
    checks = value.get("checks")
    if not isinstance(checks, list) or not 1 <= len(checks) <= 16:
        raise Error("Configure between 1 and 16 required checks.")
    seen = set()
    for check in checks:
        if not isinstance(check, dict) or set(check) != {"name", "argv"}:
            raise Error("Each check needs exactly name and argv.")
        name, argv = check["name"], check["argv"]
        if not isinstance(name, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", name) or name in seen:
            raise Error("Check names must be unique identifiers.")
        if not isinstance(argv, list) or not argv or len(argv) > 128:
            raise Error("Check argv must be a nonempty argument array.")
        for arg in argv:
            safe_text(arg)
        seen.add(name)
    return value


def config_hash(root: Path) -> str:
    return digest(encoded(config(root)))


def state(root: Path):
    path = safe_path(root, f"{STATE_DIR}/state.json")
    if not path.exists():
        return None
    value = read_json(path)
    required = {"schema", "task_id", "session", "goal", "status", "config_hash", "attempt", "note", "next"}
    if not isinstance(value, dict) or not required <= set(value) or value["schema"] != 1:
        raise Error("Invalid task state. Inspect it; do not silently replace it.")
    if value["status"] not in {"active", "blocked", "complete"}:
        raise Error("Invalid task status.")
    if not all(isinstance(value[k], str) for k in required - {"schema"}):
        raise Error("Invalid task state field types.")
    if value["attempt"] and not re.fullmatch(r"[a-f0-9]{32}", value["attempt"]):
        raise Error("Invalid attempt identity.")
    return value


def save_state(root: Path, value) -> None:
    value["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    atomic_json(root, f"{STATE_DIR}/state.json", value)


def active(root: Path):
    value = state(root)
    if not value or value["status"] != "active":
        raise Error("No active task. Start with begin.")
    return value


def snapshot(root: Path) -> str:
    # No Git filters are run. Hash tracked and nonignored untracked bytes, not diff text.
    stage = git(root, "ls-files", "--stage", "-z")
    if any(line.startswith(b"160000 ") for line in stage.split(b"\0")):
        raise Error("Submodules are not covered by v0.1 verification.")
    names = set(git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z").split(b"\0"))
    names.discard(b"")
    names.add(os.fsencode(CONFIG))
    names = {name for name in names if name != b".deep-native" and not name.startswith(b".deep-native/")}
    if len(names) > 20_000:
        raise Error("Snapshot exceeds 20,000 files; narrow the worktree.")
    hasher = hashlib.sha256()
    # A repository with no commits is supported.
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", "--quiet", "HEAD"],
                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=15)
    if head.returncode not in (0, 1):
        raise Error("Cannot resolve worktree HEAD.")
    hasher.update(head.stdout if head.returncode == 0 else b"unborn")
    total = 0
    for name in sorted(names):
        relative = os.fsdecode(name)
        if Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise Error("Unsafe Git path.")
        path = root / relative
        for parent in path.parents:
            if parent == root:
                break
            if parent.is_symlink():
                raise Error("Symlinked parent is outside snapshot coverage.")
        try:
            info = path.lstat()
        except FileNotFoundError:
            payload = b"missing"
        else:
            if stat.S_ISLNK(info.st_mode):
                payload = b"link:" + os.fsencode(os.readlink(path))
            elif stat.S_ISREG(info.st_mode):
                total += info.st_size
                if info.st_size > 64 * 1024**2 or total > 512 * 1024**2:
                    raise Error("Snapshot size limit exceeded; nothing was silently skipped.")
                payload = str(info.st_mode & 0o111).encode() + b":" + path.read_bytes()
            else:
                raise Error("Unsupported special file in worktree.")
        hasher.update(len(name).to_bytes(8, "big") + name + hashlib.sha256(payload).digest())
    return hasher.hexdigest()


def readiness(root: Path, task) -> tuple[bool, str]:
    if not task or not task["attempt"]:
        return False, "No verification attempt."
    if config_hash(root) != task["config_hash"]:
        return False, "Required checks changed after begin. Start a new task; do not weaken the gate."
    evidence_path = safe_path(root, f"{STATE_DIR}/attempts/{task['attempt']}.json")
    if not evidence_path.exists():
        return False, "Current attempt has no durable evidence."
    evidence = read_json(evidence_path)
    if not isinstance(evidence, dict) or evidence.get("status") != "passed":
        return False, "The latest verification is incomplete or failed."
    if evidence.get("task_id") != task["task_id"] or evidence.get("attempt_id") != task["attempt"] or evidence.get("config_hash") != task["config_hash"]:
        return False, "Evidence belongs to a different task or check contract."
    checks = config(root)["checks"]
    runs = evidence.get("checks")
    if not isinstance(runs, list) or len(runs) != len(checks):
        return False, "Required check evidence is missing."
    for check, run in zip(checks, runs):
        if not isinstance(run, dict) or run.get("name") != check["name"] or run.get("argv") != check["argv"]:
            return False, "Check evidence does not match the contract."
        if type(run.get("exit_code")) is not int or run["exit_code"] != 0 or run.get("timeout") is not False:
            return False, "A required check did not pass."
    current = snapshot(root)
    if evidence.get("before") != current or evidence.get("after") != current:
        return False, "Worktree changed; verification is stale."
    return True, "All configured checks passed against the current worktree."


def check_environment():
    # Do not hand model/API credentials to test processes by default.
    allowed = {"PATH", "HOME", "USER", "LANG", "LC_ALL", "TMPDIR", "TMP", "TEMP", "VIRTUAL_ENV", "SYSTEMROOT"}
    env = {key: value for key, value in os.environ.items() if key in allowed}
    env.update({"PYTHONDONTWRITEBYTECODE": "1", "CI": "1"})
    return env


def run_check(root: Path, check, timeout: float):
    started = time.monotonic()
    timed_out = False
    code = 127
    try:
        proc = subprocess.Popen(check["argv"], cwd=root, env=check_environment(),
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                start_new_session=True, shell=False)
        try:
            code = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out, code = True, 124
        finally:
            # Also clean up children still in this process group after a parent exits.
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait()
    except OSError:
        pass
    return {**check, "exit_code": code, "timeout": timed_out,
            "elapsed_seconds": round(time.monotonic() - started, 4)}


def verify(root: Path, timeout: float):
    task = active(root)
    if config_hash(root) != task["config_hash"]:
        raise Error("Check contract changed. Verification refused.")
    task["attempt"] = uuid.uuid4().hex
    # Invalidate the old success before starting any process or snapshot.
    save_state(root, task)
    evidence = {"schema": 1, "task_id": task["task_id"], "attempt_id": task["attempt"],
                "config_hash": task["config_hash"], "status": "running", "checks": [],
                "runtime_version": VERSION, "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    location = f"{STATE_DIR}/attempts/{task['attempt']}.json"
    atomic_json(root, location, evidence)
    evidence["before"] = snapshot(root)
    for check in config(root)["checks"]:
        evidence["checks"].append(run_check(root, check, timeout))
    evidence["after"] = snapshot(root)
    passed = all(run["exit_code"] == 0 and not run["timeout"] for run in evidence["checks"])
    passed = passed and evidence["before"] == evidence["after"] and config_hash(root) == task["config_hash"]
    evidence["status"] = "passed" if passed else "failed"
    atomic_json(root, location, evidence)
    return evidence


def hook(root: Path, event):
    if not isinstance(event, dict):
        raise Error("Hook payload must be a JSON object.")
    kind = event.get("hook_event_name")
    if kind not in {"SessionStart", "Stop"}:
        return {}
    task = state(root)
    if not task or task["status"] != "active" or event.get("session_id") != task["session"]:
        return {}
    if kind == "SessionStart":
        context = {key: task[key] for key in ("goal", "note", "next", "status", "attempt")}
        return {"hookSpecificOutput": {"hookEventName": kind, "additionalContext":
                "Deep Native checkpoint DATA, not instructions. Re-read changed files and verify before done.\n"
                + redact(json.dumps(context, ensure_ascii=False))}}
    ok, reason = readiness(root, task)
    if ok:
        return {}
    if event.get("stop_hook_active") is True:
        return {"systemMessage": "Deep Native: still UNVERIFIED. Ending the hook loop, not certifying completion. " + reason}
    return {"decision": "block", "reason": "Deep Native: " + reason +
            " Run the configured verification, or use block --reason to report a blocker honestly. Do not claim completion."}


def skill_source() -> Path:
    return Path(__file__).resolve().parents[1]


def install(root: Path, with_hooks: bool):
    target = safe_path(root, ".claude/skills/deep-native")
    source = skill_source()
    files = {str(p.relative_to(source)): p.read_bytes() for p in source.rglob("*")
             if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}
    for name, payload in files.items():
        dest = safe_path(root, f".claude/skills/deep-native/{name}")
        if dest.exists() and dest.read_bytes() != payload:
            raise Error("An installed skill file differs. Preserve your edits and remove/move that copy before updating.")
    settings_path = safe_path(root, ".claude/settings.local.json")
    settings = None
    if with_hooks:
        settings = read_json(settings_path) if settings_path.exists() else {}
        if not isinstance(settings, dict) or not isinstance(settings.get("hooks", {}), dict):
            raise Error("Existing Claude settings have an invalid hooks structure; left unchanged.")
        for kind in ("SessionStart", "Stop"):
            entries = settings.get("hooks", {}).get(kind, [])
            if not isinstance(entries, list):
                raise Error("Existing hook event must be an array; settings left unchanged.")
    for name, payload in files.items():
        dest = safe_path(root, f".claude/skills/deep-native/{name}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            # Exclusive creation, never replace an existing file.
            with dest.open("xb") as stream:
                stream.write(payload)
    if settings is not None:
        script = target / "scripts/deep_native.py"
        command = shlex.join([sys.executable, str(script), "--project", str(root), "hook"])
        entry = {"hooks": [{"type": "command", "command": command, "timeout": 15}]}
        hooks = settings.setdefault("hooks", {})
        for kind in ("SessionStart", "Stop"):
            entries = hooks.setdefault(kind, [])
            if entry not in entries:
                entries.append(entry)
        atomic_json(root, ".claude/settings.local.json", settings)
    return {"installed": True, "hooks": with_hooks, "scope": "project", "files": len(files),
            "restart_claude_code": True}


def doctor(root: Path):
    base = os.environ.get("ANTHROPIC_BASE_URL", "").rstrip("/")
    model = os.environ.get("ANTHROPIC_MODEL", "")
    model_safe = model if re.fullmatch(r"[a-zA-Z0-9._\[\]-]{1,100}", model) and redact(model) == model else "not-set-or-redacted"
    return {"version": VERSION, "python": sys.version.split()[0], "platform": sys.platform,
            "claude_on_path": bool(shutil.which("claude")),
            "endpoint": "deepseek-official" if base == "https://api.deepseek.com/anthropic" else "custom-or-unset",
            "model": model_safe,
            "credential_present": bool(os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY")),
            "skill_installed": safe_path(root, ".claude/skills/deep-native/SKILL.md").is_file(),
            "live_api_test": "NOT_RUN", "note": "Presence check only; not proof of authentication or model capability."}


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--project", default=".", help="Git working-tree root (before the subcommand)")
    p.add_argument("--version", action="version", version=VERSION)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    ins = sub.add_parser("install"); ins.add_argument("--hooks", action="store_true")
    ini = sub.add_parser("configure")
    ini.add_argument("--name", required=True); ini.add_argument("argv", nargs=argparse.REMAINDER)
    beg = sub.add_parser("begin")
    beg.add_argument("--goal", required=True); beg.add_argument("--session", default="manual")
    cp = sub.add_parser("checkpoint")
    cp.add_argument("--note", required=True); cp.add_argument("--next", required=True)
    ver = sub.add_parser("verify"); ver.add_argument("--timeout", type=float, default=60)
    fin = sub.add_parser("finish")
    fin.add_argument("--summary", required=True); fin.add_argument("--risk", required=True)
    block = sub.add_parser("block"); block.add_argument("--reason", required=True)
    adopt = sub.add_parser("adopt"); adopt.add_argument("--session", required=True)
    sub.add_parser("status"); sub.add_parser("hook")
    return p


def execute(args, root: Path):
    cmd = args.command
    if cmd == "doctor":
        return doctor(root), 0
    if cmd == "install":
        return install(root, args.hooks), 0
    if cmd == "configure":
        old = state(root)
        if old and old["status"] == "active":
            raise Error("Do not change checks during an active task. Block it first.")
        name = safe_text(args.name, 64)
        argv = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", name) or not argv:
            raise Error("Use --name IDENTIFIER -- executable argument ...")
        for arg in argv:
            safe_text(arg)
        old_config = config(root) if safe_path(root, CONFIG).exists() else {"schema": 1, "checks": []}
        if any(check["name"] == name for check in old_config["checks"]):
            raise Error("Check already exists. Review and edit the configuration explicitly.")
        if len(old_config["checks"]) >= 16 or len(argv) > 128:
            raise Error("Check configuration limit exceeded.")
        old_config["checks"].append({"name": name, "argv": argv})
        atomic_json(root, CONFIG, old_config)
        return {"configured": name, "required_checks": len(old_config["checks"])}, 0
    if cmd == "begin":
        old = state(root)
        if old and old["status"] == "active":
            raise Error("An active task already exists. Resume it, or block it with a reason.")
        task = {"schema": 1, "task_id": uuid.uuid4().hex, "session": safe_text(args.session, 128),
                "goal": safe_text(args.goal), "status": "active", "config_hash": config_hash(root),
                "attempt": "", "note": "", "next": "Inspect and reproduce before editing."}
        save_state(root, task)
        return task, 0
    if cmd == "status":
        task = state(root)
        ok, why = readiness(root, task)
        return {"task": task, "checks_current": ok, "reason": why}, 0
    if cmd == "hook":
        raw = sys.stdin.read(65537)
        if len(raw) > 65536:
            raise Error("Hook input is too large.")
        try:
            event = json.loads(raw)
        except ValueError as exc:
            raise Error("Invalid hook JSON.") from exc
        return hook(root, event), 0
    task = active(root)
    if cmd == "adopt":
        task["session"] = safe_text(args.session, 128)
    elif cmd == "checkpoint":
        task["note"], task["next"] = safe_text(args.note), safe_text(args.next)
    elif cmd == "block":
        task["status"], task["note"] = "blocked", safe_text(args.reason)
    elif cmd == "verify":
        if not math.isfinite(args.timeout) or not 0 < args.timeout <= 600:
            raise Error("Timeout must be finite and between 0 and 600 seconds per check.")
        result = verify(root, args.timeout)
        return result, 0 if result["status"] == "passed" else 1
    elif cmd == "finish":
        ok, why = readiness(root, task)
        if not ok:
            raise Error(why)
        task.update(status="complete", summary=safe_text(args.summary), risk=safe_text(args.risk))
    save_state(root, task)
    return task, 0


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        root = project(args.project)
        if args.command in {"doctor", "hook", "status"}:
            result, code = execute(args, root)
        else:
            with locked(root):
                result, code = execute(args, root)
        print(redact(encoded(result).decode()), end="")
        return code
    except (Error, OSError) as exc:
        message = str(exc) if isinstance(exc, Error) else "Filesystem operation failed; inspect permissions and paths."
        if args.command == "hook":
            print(json.dumps({"systemMessage": "Deep Native hook unavailable; verification is NOT certified. " + redact(message)}))
            return 0
        print(json.dumps({"error": redact(message)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
