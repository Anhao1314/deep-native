"""Offline process ownership and macOS file isolation for the benchmark runner.

Call ProcessOwner.update() while the launcher is running, including at tool/event
boundaries. Retained descendants are checked by process start identity before any
signal; cleanup also works after the launcher has exited. This observes ordinary
process trees, not unobserved double-fork daemonization between observations.

The Seatbelt profile uses a required CLI_PID parameter for Claude's native IPC
socket. A shell launcher can preserve its PID with:
    exec sandbox-exec -D CLI_PID=$$ -f PROFILE claude ...
Only that socket and the current cwd's native Claude task subtree are writable.
"""
import ctypes
import json
import os
import platform
import re
import signal
import subprocess
import sys
import tempfile
from pathlib import Path


class _BsdInfo(ctypes.Structure):
    # sys/proc_info.h: PROC_PIDTBSDINFO. Start time has microsecond precision.
    _fields_ = [('prefix', ctypes.c_uint32 * 12),
                ('comm', ctypes.c_char * 16), ('name', ctypes.c_char * 32),
                ('details', ctypes.c_uint32 * 6),
                ('start_seconds', ctypes.c_uint64), ('start_microseconds', ctypes.c_uint64)]


_darwin_library = None


def _darwin_entry(pid):
    global _darwin_library
    if _darwin_library is None:
        _darwin_library = ctypes.CDLL('/usr/lib/libproc.dylib', use_errno=True)
        _darwin_library.proc_pidinfo.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64,
                                                ctypes.c_void_p, ctypes.c_int]
        _darwin_library.proc_pidinfo.restype = ctypes.c_int
    info = _BsdInfo()
    if _darwin_library.proc_pidinfo(pid, 3, 0, ctypes.byref(info), ctypes.sizeof(info)) != ctypes.sizeof(info):
        return None
    return {'ppid': int(info.prefix[4]),
            'identity': str(info.start_seconds) + ':' + str(info.start_microseconds)}


def _process_snapshot():
    """Return parent IDs and stable start identities without command arguments."""
    if platform.system() == 'Linux':
        snapshot = {}
        for path in Path('/proc').glob('[0-9]*/stat'):
            try:
                # The comm field can contain spaces and parentheses.
                fields = path.read_text().rsplit(')', 1)[1].split()
                pid = int(path.parent.name)
                snapshot[pid] = {'ppid': int(fields[1]), 'identity': fields[19]}
            except (OSError, ValueError, IndexError):
                continue
        return snapshot
    listing = subprocess.run(
        ['ps', '-axo', 'pid=,ppid=,lstart='], capture_output=True,
        text=True, check=True,
    ).stdout
    snapshot = {}
    for line in listing.splitlines():
        fields = line.split(None, 2)
        if len(fields) != 3:
            continue
        pid = int(fields[0])
        entry = _darwin_entry(pid) if platform.system() == 'Darwin' else {'ppid': int(fields[1]), 'identity': fields[2]}
        if entry is not None:
            snapshot[pid] = entry
    return snapshot


class ProcessOwner:
    """Retain observed descendants across normal exits and forced interruption."""
    def __init__(self, proc):
        self.proc = proc
        self.owned = {}
        self.update()

    def update(self):
        snapshot = _process_snapshot()
        launcher = snapshot.get(self.proc.pid)
        if self.proc.pid not in self.owned and self.proc.poll() is None and launcher:
            self.owned[self.proc.pid] = launcher['identity']
        live = {pid for pid, identity in self.owned.items()
                if snapshot.get(pid, {}).get('identity') == identity}
        while True:
            added = {pid for pid, entry in snapshot.items()
                     if entry['ppid'] in live and pid not in live}
            if not added:
                break
            for pid in added:
                self.owned[pid] = snapshot[pid]['identity']
            live.update(added)
        return sorted(live)

    def _signal_live(self, sig):
        snapshot = _process_snapshot()
        signaled = []
        for pid, identity in self.owned.items():
            if snapshot.get(pid, {}).get('identity') != identity:
                continue
            try:
                os.kill(pid, sig)
                signaled.append(pid)
            except ProcessLookupError:
                pass
        return signaled

    def cleanup(self):
        # Freeze every still-owned process, then collect any descendants spawned
        # immediately before the freeze. Exited launchers are not an early return.
        self.update()
        for _ in range(3):
            before = set(self.owned)
            self._signal_live(signal.SIGSTOP)
            self.update()
            if set(self.owned) == before:
                break
        killed = self._signal_live(signal.SIGKILL)
        if self.proc.poll() is None:
            self.proc.wait(timeout=10)
        return {'observed_descendants': len(set(self.owned) - {self.proc.pid}),
                'signaled_pids': killed}


def claude_task_tree(root):
    """Native Claude cwd key: punctuation in the absolute cwd becomes hyphens."""
    root = Path(root).resolve()
    key = re.sub(r'[^A-Za-z0-9]', '-', str(root))
    return Path('/private/tmp') / ('claude-' + str(os.getuid())) / key


def task_output_dir(root):
    return claude_task_tree(root)


def bootstrap_temp_dirs(root):
    """Create native temp ancestors outside the sandbox before launching Claude."""
    output = task_output_dir(root)
    output.mkdir(parents=True, exist_ok=True)
    sockets = Path('/private/tmp/cc-socks')
    sockets.mkdir(parents=True, exist_ok=True)
    return {'task_output_dir': str(output), 'ipc_dir': str(sockets)}


def sandbox_profile(root, home, dependencies, port, read_only_paths=None):
    """Deny sibling answers, personal config, and all unrelated file writes.

    Dependencies and the interpreter's base prefix are read-only exceptions.
    Temp reads are limited to these runtimes, the current run, its native Claude
    task outputs and its exact IPC socket. CLI_PID must be supplied to Seatbelt.
    Literal external evaluator files can be passed in read_only_paths; neighboring
    files remain inaccessible. port=None denies all outgoing network for graders.
    """
    root = Path(root).resolve()
    home = Path(home).resolve()
    dependencies = Path(dependencies).resolve()
    personal = Path.home().resolve()
    base = root.parent
    if home != base and base not in home.parents:
        raise ValueError('Isolated HOME must be inside the current run directory')
    if port is not None and not (1 <= int(port) <= 65535):
        raise ValueError('Invalid loopback relay port')
    quote = lambda value: json.dumps(str(value))
    subpath = lambda value: '(subpath ' + quote(value) + ')'
    literal = lambda value: '(literal ' + quote(value) + ')'
    evaluator_files = [Path(path).resolve() for path in (read_only_paths or [])]
    if any(not path.is_file() for path in evaluator_files):
        raise ValueError('Read-only exceptions must be existing literal files')
    task_tree = claude_task_tree(root)
    native_parent = task_tree.parent
    sockets = Path('/private/tmp/cc-socks')
    own_socket = '(literal (string-append "/private/tmp/cc-socks/" (param "CLI_PID") ".sock"))'
    # /dev/null is needed for ordinary shell redirection. Ancestor exceptions
    # permit directory creation, without permitting arbitrary entries below it.
    writable = [subpath(base), subpath(task_tree), literal(native_parent),
                literal(sockets), own_socket, literal('/dev/null')]
    readable = [subpath(base), subpath(task_tree), subpath(dependencies),
                subpath(Path(sys.base_prefix).resolve()), literal(native_parent),
                literal(sockets), own_socket] + [literal(path) for path in evaluator_files]
    profile = '(version 1)\n(allow default)\n'
    profile += '(deny file-write* (require-all ' + ' '.join(
        '(require-not ' + path + ')' for path in writable) + '))\n'
    deny_personal = [personal / name for name in
                     ['.claude', '.claude.json', '.codex', '.ssh', '.config',
                      '.dsh', 'Library/Keychains']]
    profile += '(deny file-read-data ' + ' '.join(subpath(p) for p in deny_personal) + ')\n'
    document_exceptions = [subpath(dependencies), subpath(Path(sys.base_prefix).resolve())]
    document_exceptions += [literal(path) for path in evaluator_files]
    runtime_exclusions = ' '.join('(require-not ' + path + ')' for path in document_exceptions)
    profile += '(deny file-read-data (require-all ' + subpath(personal / 'Documents') + ' ' + runtime_exclusions + '))\n'
    temp_roots = ['/private/tmp', '/tmp', '/private/var/tmp', '/var/tmp',
                  str(Path(tempfile.gettempdir()).resolve())]
    for temp_root in dict.fromkeys(temp_roots):
        profile += '(deny file-read-data (require-all ' + subpath(temp_root) + ' ' + ' '.join(
            '(require-not ' + path + ')' for path in readable) + '))\n'
    profile += '(deny network-outbound)\n'
    if port is not None:
        profile += '(allow network-outbound (remote tcp "localhost:' + str(int(port)) + '"))\n'
    return profile
