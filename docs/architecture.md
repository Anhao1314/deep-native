# Architecture and boundaries

```text
User task + existing repository rules
                 |
       Claude Code + chosen model
                 |
      Skill (instructions, not enforcement)
                 |
      CLI (deterministic local checks)
         |                    |
  frozen check contract   task/checkpoint
         |                    |
     subprocesses -> attempt receipt -> current-worktree gate
```

There is no proxy, extra model backend, hidden reviewer API, autonomous model switch,
scheduler or new conversation store. Claude Code remains the host and its permissions
remain authoritative. The Skill's workflow is adaptive: read-only tasks do not need
a persistent lifecycle. Self-review is explicitly not an independent reviewer.

## State transitions

`configure -> begin(active) -> checkpoint* -> verify -> finish(complete)`

An unsuccessful or interrupted verify does not complete the task. Each new verification
sets a new current attempt before starting checks, invalidating the previous success.
`finish` checks the latest receipt, all check identities, the frozen configuration hash
and current source fingerprint. `block(reason)` closes the task as blocked, not complete.
`adopt` associates a deliberately resumed task with a new session. A workspace supports
one active task. Runtime mutations use a nonblocking POSIX flock.

JSON writes use temporary files, fsync and replacement. This reduces partial-file writes;
it is not a transactional database or a promise of recoverability under every disk failure.
If the filesystem fails, surface the error and inspect state before continuing. Receipts
are local records, not cryptographic attestations from an independent authority.

## Hook semantics

SessionStart injects checkpoint data for the matching active session only. Stop checks
current evidence and blocks once if absent; stop_hook_active=true returns an explicit
unverified warning and permits stopping. Corrupt input/state reports an unavailable-hook
warning. This escape avoids loops but is not enforcement of model honesty. `finish`
remains independently checkable and rejects absent/invalid/stale evidence.

Installation is project-scoped, refuses symlinked managed paths and differing existing
Skill files, and merges opt-in hook entries without tool permissions. It never edits
global model or account configuration. Source-file symlinks are fingerprinted as target
strings without following their contents. This deliberately does not verify external targets.

## v0.2 priorities

First obtain real Claude Code loading and lifecycle evidence on macOS, then repeat a
predeclared DeepSeek raw/Skill comparison on held-out tasks. Tune for observed failure
modes rather than adding more prompt text. Add native Claude as a reference only with
verified endpoint/model identity. Keep unrelated UI, automatic model routing, and
multi-agent orchestration out until they solve a measured problem.
