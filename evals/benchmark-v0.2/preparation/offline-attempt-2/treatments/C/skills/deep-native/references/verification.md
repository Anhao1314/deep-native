# What verification proves

The helper executes each configured argv array without adding a shell. It records
exit code, timeout, duration, check identity, contract hash and before/after
worktree fingerprints. It never infers success from words in a model response.
`finish` requires the latest attempt to pass all configured checks, belong to the
same task and match the current worktree and frozen contract.

Coverage: tracked files (including tracked files ignored later), deleted tracked
files, executable bits, symlink target strings, nonignored untracked files and
`.deep-native.json`. `.deep-native/` is excluded. Git HEAD is included. Untracked
ignored files, environment, external services and dependencies outside the
worktree are not covered. Submodules and special files are rejected. Large
worktrees fail explicitly at the documented limits instead of being truncated.
Tests that write nonignored artifacts change the fingerprint; ignore generated
artifacts intentionally, but do not ignore source code to evade verification.

The test environment receives only PATH, HOME, USER, LANG, LC_ALL, temporary-path
variables, VIRTUAL_ENV and SYSTEMROOT, plus CI=1 and PYTHONDONTWRITEBYTECODE=1.
Model keys are not forwarded. Test stdout/stderr are discarded, not stored. Check
commands themselves must not contain secrets. Tests can still read the filesystem
and access networks: this is NOT a sandbox. Run only trusted commands/patches or
use an actual OS/container sandbox with network and credential isolation.

A check that exits zero after doing nothing can still pass. Humans must choose
meaningful commands and review test changes. An agent with write access can alter
state, scripts and receipts. Hashes detect accidental staleness, not malicious
forgery. These are local receipts, not signed attestations or an independent judge.

The optional Stop hook blocks once when an active matching-session task lacks
current evidence. On stop_hook_active=true it warns and permits stopping to avoid
loops. Hook read/parse/lock/permission errors warn and do not trap the user. This
never turns an unverified task into a verified one. The CLI `finish` remains the
fail-closed completion check. Hook behavior does not certify model compliance.
