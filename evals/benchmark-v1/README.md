# Pilot Benchmark v1

**Same DeepSeek model, task, budgets, and environment. One treatment: Deep Native.**

This harness performs real Claude Code calls to the official DeepSeek Anthropic
endpoint. It does not generate mock agent results. Offline reference repairs only
validate the independent grader and are never provided to agents.

## Scope and frozen design

- 10 curated coding tasks × 3 repetitions × A/B = **60 planned runs**.
- A: Claude Code + DeepSeek, no Deep Native skill, hooks, instructions or state.
- B: same setup, with the unmodified skill and optional SessionStart/Stop hooks
  from `fda3dd010e7de8f8c1ee1953e006e577464aa3d6`.
- B activation is one fixed system append: `Use the installed deep-native skill
  for this task.` It contains no extra workflow advice. Native Skill loading is
  checked through actual successful Skill tool events. Merely installing a folder
  does not attest activation. A/B user prompts are byte-identical.
- Model: CLI `deepseek-flash[1m]`; observed official API request/response model
  `deepseek-flash`. Endpoint `https://api.deepseek.com/anthropic`.
- Claude Code 2.1.289; effort `max`; API thinking request, maximum output tokens,
  and any temperature setting are recorded per call, without translation.
- Each run has **24 assistant-turn** and **480 agent wall-second** ceilings.
  Setup and independent grading are separately timed. No claimed dollar ceiling:
  Claude's cost basis is unknown for this provider. Cost remains unavailable.
- Seed `20261006`: shuffled task order within each repetition, independently
  randomized A/B order within each adjacent task pair. The full schedule is saved
  before the first formal call. Execution is sequential to avoid resource contention.
- Tasks, grading code, runner, analysis and schedule are hash-frozen before formal
  execution. Deep Native is exported directly from its fixed Git commit. No
  benchmark-specific Deep Native changes are permitted during a campaign.

This is a **curated pilot**, not a historical issue benchmark. It uses boltons and
more-itertools, both independent public Python utility repositories. Three tasks
inject labelled regressions into real source; seven define maintenance extensions
or refactoring requirements. The long task covers API/parser/CLI/regression work
within minutes, not a multi-hour application. These limits materially constrain
generalization.

| ID | Capability | Repository | Intervention / acceptance |
| --- | --- | --- | --- |
| T01 | Simple bug fix | boltons | Injected ordinal suffix regression; signed numeric/string/ext_only contracts |
| T02 | Edge validation | more-itertools | Strict size types before iterator consumption, old valid behavior retained |
| T03 | Cross-file bug | more-itertools | Injected public-import alias and suffix corruption; both import paths checked |
| T04 | Feature | boltons | Signed integer/range grammar, literal delimiters, errors and duplicates |
| T05 | Refactor + regression | more-itertools | One accumulation loop, preserved callbacks/order/defaultdict, new test required |
| T06 | Unfamiliar investigation | boltons | Injected nested-lookup regression; defaults, dotted indexing and error details |
| T07 | Error recovery | more-itertools | Real check command exits 69 once, then normal checks; public lazy iterator feature |
| T08 | Multiple-step task | boltons | Signed parser reuse, canonical range API, CLI expand/compact and error handling |
| T09 | Verification staleness | more-itertools | Implement/check padded chunks, then real follow-up changes API with `pad=False` |
| T10 | Interruption/recovery | more-itertools | Real SIGKILL following source mutation, then a new Claude session implements/continues runs API |

Exact prompts, upstream URLs and full commits, allowed source files, and seeded
mutations are in [tasks.json](tasks.json) and [fixtures.py](fixtures.py).
Each workspace has a deterministic fixture Git commit consisting of the upstream
tree, any seeded fault, and visible check scripts. That commit must match across
arms/repeats. Agents can add regression tests under `agent_tests/` and relevant
documentation. Existing tests, benchmark checks and repository configuration are
protected. Missing files, symlinks, test changes or out-of-scope modifications fail.

## Actual interventions

T07's first real `python3 benchmark_check.py` call creates an ignored marker and
exits 69. The next call runs the actual tests. The independent grader bypasses this
infrastructure fault. Recovery of this failure is an observed event, not a claim
made in a prompt.

T09 uses two real stages in the same resumed session. Stage 1 receives at most 18
of the total 24 turns. After the process stops, the runner independently grades
stage 1 and sends the identical follow-up to both arms. Stage 2 receives the
remaining turns and seconds. Actual later source mutation and stage-1 pass are
recorded. Cases without a green first stage or later code edit cannot establish
verification-staleness effectiveness. The primary final score still includes them.
The final verifier checks the newly requested behavior, not the old visible test.

T10 kills the actual Claude process group after the first source mutation and one
further completed tool-result event. A 90-second fallback interruption applies if
that event has not occurred. The second session gets the same original task with
`Continue working on this task:` prepended; it receives no previous transcript.
The source tree remains, and only B has any Deep Native state. Total turns/seconds
are shared between sessions. Interruption, intermediate patch/state, distinct
session IDs, and presence of checkpoint notes are retained. If no interruption
actually occurs, the recovery mechanism is not claimed as tested in that run.

## Isolation and credentials

Live execution currently supports macOS with `sandbox-exec` (Seatbelt).
Every run has a fresh `/private/tmp/dn-live-*/` workspace, HOME, Claude config,
temporary directory and sessions. None is reused. No ancestor has repository
instructions; preparation rejects upstream CLAUDE.md, AGENTS.md or `.claude` trees
unless a new protocol explicitly audits them.

Only project/local setting sources are enabled. MCP is strictly empty, auto-memory
and auto-updates are disabled, and both arms have the same explicit tool allowlist:
Bash, Read, Edit, Write, Glob, Grep, Skill. Permission mode is `dontAsk` with these
tools explicitly allowed; permission bypass is not used. Built-in Claude skills
and plugins remain present in both arms and their init events are retained.

Seatbelt denies reading personal Claude/Codex/SSH/DSH/config/keychain data and the
experiment directory, with narrowly defined read-only Python/dependency exceptions.
The agent's outgoing network is limited to the loopback relay port. The relay
alone calls the official DeepSeek endpoint. It keeps the upstream credential only
in parent process memory. Agents get the non-secret string `benchmark-local-relay`,
never the user's API key. Request bodies and authentication headers are not logged.
Shell startup configuration, unrelated credentials and Python paths are not inherited.
This is a pragmatic isolation boundary, not a proof against hostile model programs.

The independent grader copies candidate files into another fresh directory, checks
external contracts and the unchanged upstream regression suites. Protected-file
hashes and allowed modification scope are separate necessary PASS conditions.
Deep Native receipts and self-reported test outcomes do not establish success.

## Reproduce

Python 3.12.14 was used locally. The current `python3` system binary may be older;
ensure the agent PATH starts with the chosen environment's bin directory.

```bash
python3.12 -m venv /tmp/dn-eval-env
/tmp/dn-eval-env/bin/python -m pip install \
  pytest==8.3.5 pluggy==1.6.0 packaging==26.3 iniconfig==2.3.0

# Existing local Claude settings contain your official DeepSeek credentials.
# Never place credentials in this repository or command-line arguments.
OUT="$PWD/evals/benchmark-v1/results/my-campaign"
PY=/tmp/dn-eval-env/bin/python
CACHE=/tmp/dn-benchmark-cache
python3 evals/benchmark-v1/harness.py freeze --output "$OUT" \
  --python "$PY" --cache "$CACHE"
python3 evals/benchmark-v1/harness.py run --output "$OUT" \
  --python "$PY" --cache "$CACHE"
python3 evals/benchmark-v1/harness.py analyze --output "$OUT"
```

The config defaults to `~/.claude/settings.json`; `--provider-config` selects an
explicit existing local file. No credential search is performed. The endpoint must
be the audited official one. `--limit N` runs the next N scheduled runs without
overwriting previous artifacts. Missing runs remain missing. A partial directory
without result.json stops reuse; diagnose it and retain the evidence. For a runner,
task or skill change, create a new campaign rather than mixing protocols.

The CLI/model alias and server weights can change over time. Reproduction means
repeating the frozen procedure and reporting actual versions/identities, not
promising identical stochastic outputs or unobservable fixed model weights.

## Artifacts and scoring

The campaign directory contains audit.json, tasks.json, baselines.json,
schedule.json, freeze.json and the exported treatment. Each run saves:

- Exact user prompts, command arguments and sanitized environment metadata.
- Full stream-json transcripts, tool calls/results, hook events, final responses.
- API request model/configuration and actual server SSE token usage.
- Tests before/after, external contract outcomes and upstream regression output.
- Final patch including new files, changed-file/line counts, artifact SHA-256 hashes.
- Agent and inclusive setup/grading durations, source fingerprints at tool returns.
- Actual interruption/recovery and staleness evidence when applicable.

Strict Task Success is PASS iff independent contracts **and** upstream regressions
pass, with protected tests intact and modifications allowed. Everything else is
FAIL; failures and budget exhaustion are retained.

`declared_done` uses the common final `STATUS: DONE` marker; `STATUS: BLOCKED` is
false and missing markers are unknown. **Verified Completion Rate** is independently
valid declared completions / all declared completions. The report also publishes
valid declared completions / all runs, false completions, and unknown declarations.

Behavior is derived from actual tool events: investigation before edit, reproduction
before edit, verification, continued work after a failed check, source edits after
verification, and explicit risk language. Command parsing and output patterns are
proxies and can miss custom test invocations. Unsupported test-claim language is
flagged for trace review; it is not automatically labelled fabrication. Full trace
evidence is preserved for human review.

SSE input/output/cache token counts are recorded only when all relevant responses
complete; partial interrupted usage is **unavailable**, never estimated. CLI cost
telemetry is retained as diagnostics but `costBasis: unknown` is not real billing.
Tokens include cached input when comparing total context processing; cache categories
are also published so this cannot be mistaken for equal-cost billable tokens.

Reports are regenerated exclusively from run artifacts into summary.json,
results.jsonl, results.csv, REPORT.md and success.svg. Primary uncertainty is a
20,000-sample paired bootstrap over task clusters (seed 91271), preserving all three
repeats per sampled task. Wilson run-rate intervals are descriptive because runs on
the same task are correlated. No parity or statistical-superiority claim is made.

Frozen final judgment: PASS with a positive task-cluster interval, FAIL with a
negative interval or no differing paired outcomes after the complete 60 runs,
INCONCLUSIVE otherwise. Incomplete execution or configuration/activation validity
issues force INCONCLUSIVE. Recovery/staleness counts are reported separately.

## Retained initial campaign and isolation repair

The first campaign stopped after **2 completed runs and 1 partial run** when
process inspection showed that Claude's background Bash descendants can have a
different process group from the launcher. The original runner only killed the
launcher group, which was insufficient for reliable future forced interruptions.
The entire initial campaign is excluded from the primary A/B comparison and its
[artifacts and stop record](results/2026-10-06-pilot/campaign_stop.json) are retained.
No observed descendant leaked into a subsequent completed run; this repair closes
the identified termination gap before the recovery tasks are executed.

The replacement campaign is `results/2026-10-06-pilot-v2/` and restarts the entire
60-run schedule. Task definitions, seed, prompts, budgets, model configuration and
Deep Native commit remain identical. Only process cleanup changed: stop the
launcher, collect/stop its descendants (including separate groups), then kill
the descendants and launcher. An offline real-subprocess test verifies that a
detached child is terminated. This is a harness isolation repair, not Skill tuning.

## Validate the harness without calling a model

```bash
python3 -m unittest discover -s tests -v
# Optional full grader validation using cached fixed upstream commits:
DN_BENCHMARK_CACHE=/tmp/dn-benchmark-cache \
DN_BENCHMARK_PYTHON=/tmp/dn-eval-env/bin/python \
  python3 -m unittest discover -s tests -p test_benchmark_v1.py -v
```

The full fixture check requires cache directories named `boltons` and `more`.
It rejects all 10 initial fixtures and accepts the explicit offline reference
repairs. This validates grader mechanics, not model performance. Original Deep
Native runtime/demo tests remain part of CI.
