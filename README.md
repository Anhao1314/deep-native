# Deep Native

**Evidence-first coding for DeepSeek in Claude Code.**

[中文说明](README.zh-CN.md) · [中文完整教程](docs/tutorial.zh-CN.md) · [Executed demo](docs/demo/demo.html) · [Test report](docs/validation.md) · [Evaluation protocol](evals/README.md)

> **No evidence, no done.**
> A small Skill plus local verification tools. Not a model upgrade, not a Claude clone,
> and not a claim that DeepSeek now matches Claude.

```text
Inspect -> Reproduce -> Edit -> Verify -> Review -> Deliver
                              |
                   current code + required checks
                              |
                   evidence receipt, not a promise
```

## What ships in v0.1.0

| Component | What it actually does |
| --- | --- |
| `SKILL.md` | A bounded, adaptive coding workflow: investigate first, verify before done, report blockers honestly |
| `doctor` | Read-only configuration presence checks; no API request or secret output |
| `install` | Project-scoped Skill installation; no global settings or model changes |
| Check contract | Named required commands, frozen when a task begins |
| `verify` / `finish` | Actual subprocess checks, exit codes, timeouts, worktree fingerprints, stale-result rejection |
| Checkpoint / recovery | Small persisted progress notes; optional matching-session recovery hook |
| Optional Stop hook | One continuation reminder, then explicit unverified escape to avoid loops |
| Demo / grader | A real offline scripted replay and equal fixtures for future model comparisons |

The helper uses Python's standard library. Runtime support: **Python 3.10+ on macOS/Linux**,
Git, and a trusted repository. Windows runtime support is not claimed; use WSL.
The Skill itself has no package dependency, but the evidence helper requires Python.

## Try the offline demo first

No Claude installation, API key or model bill required:

```bash
git clone https://github.com/Anhao1314/deep-native.git
cd deep-native
python3 -m unittest discover -s tests -v
python3 examples/demo.py --output artifacts/demo
```

Open `artifacts/demo/demo.html` locally. On macOS:

```bash
open artifacts/demo/demo.html
```

The demo executes failing tests, rejects premature completion, applies an explicitly
**scripted** repair, restores a checkpoint, verifies, rejects evidence after a later
edit, and verifies again. Twelve recorded steps, not an animation pretending to be an
agent. The checked-in [JSON transcript](docs/demo/demo.json) is inspectable.

## Install into an existing Claude Code project

Already running Claude Code through DeepSeek? **Keep your working provider setup.**
This project does not need your API key and does not change model settings.

```bash
# From this cloned deep-native directory:
PROJECT="/absolute/path/to/your/git-project"
python3 deep_native.py --project "$PROJECT" doctor
python3 deep_native.py --project "$PROJECT" install
```

Restart Claude Code in that project and invoke:

```text
/deep-native Fix the retry behavior. Inspect first, add a regression test,
verify the actual change, and report any untested limitations.
```

For optional session recovery and a bounded Stop reminder:

```bash
python3 deep_native.py --project "$PROJECT" install --hooks
```

This merges only our entries into `.claude/settings.local.json`, preserves unrelated
settings, and grants no tools or permission bypass. Inspect the file before restarting.
Different existing Skill files are never overwritten. See [installation and removal](docs/tutorial.zh-CN.md).

## Manual evidence workflow

Configure the **real test command for your project**, not a command that simply exits zero.
This example uses a Python unittest project:

```bash
DN="$PWD/deep_native.py"
python3 "$DN" --project "$PROJECT" configure --name tests -- python3 -m unittest discover -s tests
python3 "$DN" --project "$PROJECT" begin --goal "Fix retry semantics without regressions"
# Make and inspect the actual change.
python3 "$DN" --project "$PROJECT" checkpoint --note "Located and fixed boundary condition" --next "Run regression suite"
python3 "$DN" --project "$PROJECT" verify --timeout 60
python3 "$DN" --project "$PROJECT" finish --summary "Retry semantics fixed" --risk "Provider integration not tested"
```

`--project` goes **before** the subcommand. `configure` accepts argv after `--`, not a
shell string. Add multiple named checks before `begin`; every configured check is
required. For hook activation the Skill supplies Claude Code's current session ID.
The manual CLI session defaults to `manual` and does not attach to an arbitrary session.

Exit codes: **0** successful command, **1** verification failed, **2** invalid input,
blocked completion or runtime error. Hook errors are reported as warnings with exit 0
so a broken hook cannot trap the user; they never certify success.

## What has and has not been measured

| Experiment | Status |
| --- | --- |
| Runtime, installer, failure-path and fixture-grader tests | See [actual validation report](docs/validation.md) |
| Offline scripted repair and stale-evidence demo | Executed; [12-step transcript](docs/demo/demo.json) |
| Three-arm fixture identity / external grader | Tested locally |
| Actual Claude Code Skill loading and hook lifecycle | **NOT RUN in the authoring environment** |
| DeepSeek raw vs DeepSeek + Skill vs native Claude | **NOT RUN** |
| Model accuracy, token savings, cost savings, native parity | **No claim** |

The development environment had no Claude executable, model credentials or external
DNS access. Unit tests and hook payload simulations are **not** live host validation.
The [evaluation protocol](evals/README.md) explains how to run the missing comparisons
without passing off fixture tests as model performance.

## Limits that matter

Verification covers Git-tracked and nonignored untracked worktree bytes, the check
contract, symlink targets and executable bits. It excludes local state and untracked
ignored files. External services, dependencies and environment changes are not covered.
Submodules and oversized worktrees fail explicitly. See [coverage details](skills/deep-native/references/verification.md).

Checks run real programs. This is **not a sandbox**. Do not run untrusted repositories
or model patches without OS/container isolation. The wrapper does not forward model
credentials to checks and does not store test stdout/stderr, but programs can still
read files or contact networks. Local receipts are not signed or tamper-proof; an agent
with filesystem access can forge them. Use independent CI and code review for trust.

A Skill cannot supply unsupported API capabilities, larger model intelligence or
perfect instruction following. Extra planning/checks can increase latency and token
usage. Tiny read-only tasks should not pay for a full task lifecycle.

## Project layout

```text
skills/deep-native/      Installable Skill, references and standalone helper
deep_native.py          Zero-install CLI entry point
tests/                  Offline regression and negative tests
examples/demo.py        Executed fixture -> HTML and JSON replay
evals/                  Equal workspaces and external patch grader
docs/                   Tutorial, validation, architecture, sources and replay
.github/workflows/      CI definition; workflow status is separate from local results
```

## Contributing

Start with a reproducible failure and a failing test. Keep the Skill small and preserve
existing permissions. Do not submit credentials, conversation transcripts or fabricated
benchmark results. See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

Licensed under MIT. Independent project; not affiliated with or endorsed by Anthropic
or DeepSeek. The aspiration is native-like workflow reliability; any improvement must
be demonstrated on held-out tasks, not inferred from the project name.
