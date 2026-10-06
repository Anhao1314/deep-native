# Deep Native

**Adaptive coding behavior for DeepSeek in Claude Code.**

[中文说明](README.zh-CN.md) · [中文教程](docs/tutorial.zh-CN.md) · [Architecture](docs/architecture.md) · [v0.1 pilot findings](docs/v0.1-pilot-findings.md) · [v0.2 ablation plan](evals/v0.2-ablation.md)

> **Do less by default. Escalate when evidence demands it.**
>
> Deep Native is a Skill plus deterministic local verification tools. It is not a
> model-weight upgrade, not a Claude clone, and not a claim that DeepSeek matches Claude.

## Why v0.2 Candidate exists

The first live A/B pilot did **not** show a quality improvement for v0.1. In the
10 complete pairs, Raw DeepSeek passed **8/10** and Deep Native v0.1 passed **7/10**.
The Skill made the agent more persistent after failures, but also increased tool use
and paired processing overhead without converting that extra work into more task wins.

That negative result changed the design.

```text
                         task
                          |
                   choose lightest mode
                 /          |           \
              FAST       STANDARD       DEEP
              local       uncertain      long/high-risk
                |            |              |
          edit + check   hypothesis +   checkpoint +
                         verification     evidence runtime
                 \          |           /
                       fresh evidence
                          |
                        deliver
```

Raw pilot artifacts remain on the
[`benchmark-v1` branch](https://github.com/Anhao1314/deep-native/tree/benchmark-v1).
The product branch keeps only the measured conclusions, not 370k+ lines of experiment
artifacts.

## Three modes

| Mode | Use when | Persistent Deep Native runtime |
| --- | --- | --- |
| **FAST** | Localized, clear, low-risk, no failed attempt | No |
| **STANDARD** | Cross-file, uncertain root cause, or first failed attempt | No by default |
| **DEEP** | >=2 ineffective attempts, repo-wide, long-running/high-risk, interruption risk | Yes |

FAST is intentionally boring:

```text
inspect -> edit -> focused check -> deliver
```

STANDARD adds explicit reproduction/hypothesis handling and a broader relevant check.
DEEP activates the existing frozen check contract, checkpoints, worktree-bound
verification, stale-evidence rejection, and optional recovery hooks.

## Failure classification

v0.2 Candidate distinguishes:

`implementation · hypothesis · contract · environment · dependency · budget · unknown`

The distinction is operational. An environment failure such as a denied temp path
should change the invocation or writable path before product code is touched.
A second ineffective attempt is an escalation signal, not permission to loop.

The installable Skill contains
[`scripts/policy.py`](skills/deep-native/scripts/policy.py), a deterministic mirror of
the routing/failure rules used by tests and evals. Normal tasks do not need another tool
call just to “prove” they chose a mode.

## Stable evidence layer

The v0.1 deterministic helper remains deliberately stable in this candidate. For DEEP
tasks it can:

- freeze named project checks when a task begins;
- save small recovery checkpoints;
- run required checks without a shell wrapper;
- record exit code, timeout, contract identity, and worktree fingerprints;
- reject completion when evidence is missing, failed, or stale;
- optionally remind a matching Claude Code session before it stops unverified.

This separation matters: v0.2 is changing the **behavior policy**, not rewriting the
already-tested evidence gate merely to improve benchmark scores.

## Install

Requires Python 3.10+, Git, macOS/Linux (or WSL for the runtime helper).

```bash
git clone https://github.com/Anhao1314/deep-native.git
cd deep-native

PROJECT="/absolute/path/to/your/git-project"
python3 deep_native.py --project "$PROJECT" doctor
python3 deep_native.py --project "$PROJECT" install
```

Restart Claude Code in the target project. Then:

```text
/deep-native Fix the retry bug with the smallest safe workflow. Escalate only if the evidence requires it.
```

For long-running DEEP work, optional recovery/Stop hooks can be installed with:

```bash
python3 deep_native.py --project "$PROJECT" install --hooks
```

The installer is project-scoped. It does not alter global model settings, buy access,
set API keys, grant tools, or bypass permissions.

## DEEP manual evidence workflow

Only use the persistent lifecycle when the task actually needs it.

```bash
DN="$PWD/deep_native.py"

python3 "$DN" --project "$PROJECT" configure --name tests -- python3 -m unittest discover -s tests
python3 "$DN" --project "$PROJECT" begin --goal "Fix retry semantics without regressions"
python3 "$DN" --project "$PROJECT" checkpoint \
  --note "Confirmed boundary bug; current hypothesis X; changed retry.py and test_retry.py" \
  --next "Run focused regression and inspect failure if any"
python3 "$DN" --project "$PROJECT" verify --timeout 60
python3 "$DN" --project "$PROJECT" finish \
  --summary "Retry semantics fixed" --risk "Provider integration not tested"
```

FAST and STANDARD tasks should not pay this lifecycle cost by default.

## Live preliminary evidence

The stopped v0.1 campaign retained 21 runs. Matched comparison:

| Metric | Raw DeepSeek | Deep Native v0.1 |
| --- | ---: | ---: |
| Strict task success | **8/10** | **7/10** |
| Pairwise quality wins | — | **0 win / 1 loss / 9 ties** |
| Median tool calls | 29 | 36 |
| Continued after actual failed check | 4/5 | 10/10 |

Paired median B/A ratios were approximately **1.20x** for agent time and **1.21x**
for context-processing tokens. The run also exposed 17 shell/temp denials and invalid
measurement of the intended stale-verification/recovery mechanisms. Therefore the
formal result remains **inconclusive**, and v0.2 is a hypothesis derived from traces,
not a claimed improvement.

See [the full product-side findings](docs/v0.1-pilot-findings.md).

## Next experiment

Do **not** jump back to 60 runs. The next experiment is a 12-run mechanism ablation:

`Raw DeepSeek vs v0.1 vs v0.2 Candidate`

on four held-out tasks targeting hard debugging, environment classification, fresh
verification, and recovery after real progress.

See [evals/v0.2-ablation.md](evals/v0.2-ablation.md).

## Limits

A Skill cannot create model intelligence that the base model does not have. More
planning and more tool calls are not automatically better.

The evidence helper is not a security sandbox or signed attestation. Checks can be
insufficient even when they exit zero. External services, ignored untracked files,
dependencies, and environment changes are outside the worktree fingerprint. Use
independent tests, CI, and review for consequential changes.

## Project layout

```text
skills/deep-native/
  SKILL.md                    adaptive agent behavior
  references/
    adaptive-runtime.md       routing/failure policy
    recovery.md
    verification.md
  scripts/
    policy.py                 deterministic policy mirror
    deep_native.py            stable evidence runtime

tests/                        offline regression tests
docs/                         architecture, tutorial, pilot findings
evals/                        benchmark protocol and ablations
benchmark-v1 branch           retained live raw artifacts
```

## Development rule

Do not optimize the Skill against a frozen benchmark and then call the same tasks
held-out evidence. Every candidate change gets a new commit and a new held-out set.

Licensed under MIT. Independent project; not affiliated with or endorsed by Anthropic
or DeepSeek.
