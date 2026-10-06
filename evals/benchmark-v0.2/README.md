# v0.2 held-out mechanism discovery ablation

Exactly four new cachetools tasks × A/B/C × one observation, with no automatic expansion. This is not a statistical efficacy claim. The behavior layers were fixed before task construction: A raw, B fda3dd010e7de8f8c1ee1953e006e577464aa3d6, C 824c3009e465a1748250f5ed8589e096237dcb08. No Skill code is edited.

`campaign/manifest.json` records verbatim prompts, commits and budgets; `schedule.json` fixes order using seed 20261007. `freeze.json` hashes executable experimental inputs. `preparation/issue-2.json` and ../v0.2-ablation.md are the governing specification. Preparation failures are retained separately and involved zero model calls.

All arms use the same native Claude Code, explicit DeepSeek endpoint/model, max effort, tools, permissions, isolated home, source fixture commit, Python dependencies, writable scratch setup and relay. Only installation/activation of the pinned behavior layer differs. Native treatment verification deliberately uses its unchanged environment filtering; the common check entrypoint explicitly sets its own source import path for child tests. A native BSD mktemp wrapper supplies documented `-p "$TMPDIR"`; zsh heredocs also have a per-run TMPPREFIX. Loopback test sockets work. Sibling experiment workspaces and personal instruction/credential files remain unavailable.

## Tasks and strict acceptance

- D1: four seeded cross-key condition-wait regressions across function/method and info variants; preserve upstream behavior, same-key suppression, cleanup and independent-key progress. Initial LRU hypothesis is deliberately unconfirmed. Trace review checks whether evidence actually discriminates causes.
- E1: a nonwritable fixture is the launcher's erroneous default temp parent. Product tests pass initially, launcher fails before them. A corrected invocation or launcher plus actual completed checks and unchanged product is a success. The intended permission error is not an infrastructure failure.
- F1: actual functional phase-one pass, then runner changes the relevant acceptance tests. Resume the same session to add strict atomic behavior. Final independent acceptance and a completed meaningful check on final source/test bytes are both required.
- R1: actual snapshot functionality passes two milestone categories while full restore acceptance still fails (2/4 milestones, approximately 50%; not a lines-of-code percentage). After substantive retained notes/checkpoint, SIGKILL owned processes. Continue with a new session ID and no transcript injection. The same continuation directs all arms to use saved progress. B/C require a native checkpoint; raw may use PROGRESS.md. A failure to reach this gate within budget remains a failed/nonqualifying observation; no timer fabricates a recovery event.

A protected runner records source/check hashes before and after real task tests, upstream pytest and any submitted agent tests. A passing receipt must also have completed tool-output or native verify-attempt corroboration. Version/help, background launches, and empty exit-zero commands never qualify. Independent grading copies permitted implementation bytes into a clean fixture, uses canonical task/upstream contracts, and checks submitted regression tests. Protected-file and scope violations fail strict acceptance. Full traces and patches remain the review source; receipts are not cryptographic adversarial attestations.

## Budget and intervention

48 upstream generation attempts and 900 elapsed session seconds per run, shared across phases. For staged tasks, phase one has at most 28 Claude turns and 540 seconds. Relay refuses a 49th upstream generation attempt. Provider interruptions with missing terminal usage make total tokens unavailable; partial usage is retained without filling missing values. No reliable billing source is configured: cost is unavailable. Experiment grading at the intervention boundary is included in elapsed session time and documented.

Interventions occur at an observed tool-result boundary with processes briefly stopped to verify actual progress. F1 restarts the same conversation; R1 uses a new ID. SIGKILL may interrupt a provider response already in flight; such usage remains incomplete. All run directories are append-only, and incomplete runs cannot silently restart. A contamination stop requires preservation, repair, a new freeze and a new entire comparison, never pooling excluded observations.

## Decision rule fixed before model calls

A clear C mechanism win means a correct category/adaptation where another arm fails, fresh final verification where another arm lacks it, successful checkpoint-informed recovery where another arm fails, a discriminating root-cause correction missed by another arm, or at least 30% fewer v0.1 runtime-ceremony calls with equal correctness and adequate verification. Interpret observed wins with the four-task/single-observation limitation.

CONTINUE only with a clear C mechanism win, no compensating strict quality loss and explainable overhead. ANALYZE for ties with mixed trace effects. STOP for a new C strict-quality loss or added work without mechanism wins. Report both functional acceptance and stricter task completion, every arm/task, provider usage availability, tool calls, repeated actions, product-code damage, checkpoints, freshness and final claims. No post-hoc Skill tuning or selective reruns.

## Reproduction

Use the frozen public upstream SHA and treatment archives. A local Python 3.12 environment with the pinned dependencies in audit.json and native Claude version is required. Adapt the explicit workspace paths in harness.py before creating a new freeze (this constitutes a new experiment), and supply the official DeepSeek configuration in ~/.claude/settings.json. `harness.py freeze` performs offline calibration, `test_harness.py` validates treatment execution/freshness, and `runtime.py` executes exactly the frozen schedule. Authentication is kept in parent memory; children receive only a dummy loopback credential. Never commit real credentials.
