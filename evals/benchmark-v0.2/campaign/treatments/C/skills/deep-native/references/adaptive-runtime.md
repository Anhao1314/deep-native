# Adaptive Runtime policy

Deep Native v0.2 Candidate uses escalation instead of mandatory ceremony.

## Modes

| Mode | Typical signals | Persistent runtime? | Verification |
| --- | --- | --- | --- |
| FAST | Localized, clear acceptance, low risk, no failed attempt | No | One meaningful focused check, plus existing required checks when obvious |
| STANDARD | Cross-file, uncertain root cause, or first failed attempt | No by default | Focused check followed by the relevant broader check |
| DEEP | >=2 ineffective attempts, repo-wide scope, long-running/high-risk work, interruption risk | Yes | Frozen check contract + current-worktree evidence |

A task may start FAST and escalate. It should not de-escalate merely to avoid
verification after risk has become visible.

## Escalation signals

Escalate to DEEP when:

- the second ineffective repair/check attempt occurs;
- the task expands to repo-wide or several subsystems;
- compaction, restart, or handoff is likely;
- the change becomes difficult to reverse;
- a high-risk migration/security/data-integrity path is involved.

An isolated shell or sandbox error is not automatically a DEEP signal. Classify it
as environment first and adapt the invocation.

## Failure classes

**implementation**  
The current hypothesis is still plausible and the failure points to the patch.
Inspect the diff and failing behavior, make the smallest correction, then rerun a
focused check.

**hypothesis**  
The observed failure contradicts the current explanation. Stop editing. Re-read the
relevant code/output and create an alternative hypothesis before the next code change.

**contract**  
The implementation may not satisfy the actual acceptance condition. Re-read existing
tests/specs. Never delete, skip, dilute, or redefine requirements to obtain green output.

**environment**  
The command did not execute under the current shell, sandbox, writable path, or runtime.
Adapt the command/environment before touching product code. A heredoc denial, missing
temporary directory, or permission failure is not evidence that application code is wrong.

**dependency**  
The task depends on an unavailable or incompatible runtime/package/service. Repair the
dependency only when authorized; otherwise report the blocker.

**budget**  
Time/turn/context budget is ending. Save confirmed facts, current hypothesis, changed
files, and one next action. Do not rush an unverified completion.

**unknown**  
Collect one new discriminating observation. Do not issue the same unchanged failing
command repeatedly.

The optional `scripts/policy.py` is a deterministic mirror of this table. It exists
for auditing and evals; calling it is not required on normal tasks.
