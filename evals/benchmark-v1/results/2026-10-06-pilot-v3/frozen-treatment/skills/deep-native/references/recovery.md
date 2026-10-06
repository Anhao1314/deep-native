# Recovery, without a second source of truth

`state.json` holds one active task, its session, goal, frozen check-contract hash,
latest attempt identity, progress note and next action. It does not contain a
conversation transcript, hidden reasoning or API credentials.

1. Read `status`. A failed read is a blocker, not an empty task.
2. Re-read the relevant source and `git diff`. Stored notes may be stale.
3. If continuing the same task in a new Claude Code session, call `adopt --session`
   with that session's actual identifier. Never adopt another person's work blindly.
4. Resume the next concrete action; verify again after edits.

An optional SessionStart hook injects a small checkpoint only for the matching
active session, including after compaction. Other sessions are not hijacked. For
parallel work, use separate Git worktrees. The CLI rejects concurrent writes with
a nonblocking filesystem lock. A checkpoint is not automatic rollback or a backup
of files; use Git for code history.

If the helper cannot run, preserve the existing files, report the failure and
continue only within the user's instructions. Do not silently delete corrupted
state. `block --reason` closes an active task as blocked, allowing a new task while
retaining old attempt receipts. Do not label a blocked task completed.
