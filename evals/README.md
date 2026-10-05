# Evaluation: separate tool correctness from model capability

## Current evidence

The offline tests prove local helper behavior and that the external fixture grader
rejects the seeded bugs and accepts a scripted reference repair. They do not show
that a model can produce that repair. **No model-comparison results are published.**

This initial fixture has three small function contracts and 12 external test methods.
It is a diagnostic smoke test, not a representative software-engineering benchmark.
It cannot establish parity, production quality, cost savings or statistical superiority.

## Prepare equal workspaces

Run from the deep-native checkout. Use fresh paths OUTSIDE that checkout so the raw
arm cannot inherit its Skill through a parent directory:

```bash
python3 evals/bench.py prepare --arm raw --workspace /tmp/dn-raw-01
python3 evals/bench.py prepare --arm skill --workspace /tmp/dn-skill-01
python3 evals/bench.py prepare --arm claude --workspace /tmp/dn-claude-01
```

Source and task hashes match across arms. Only the skill arm receives the Skill.
No hooks are installed by this experiment: it tests the Skill plus its explicit helper,
not a separate hook treatment. Add a fourth arm for hooks rather than changing an arm
halfway through. Sidecar manifests are written next to, not inside, the workspaces.

## Run the agents yourself in a credentialed environment

Use fresh Claude Code sessions and isolated user configuration for each arm. Inspect
`claude --help` and the official settings documentation for your installed version;
record the exact CLI version and settings-source choices. Do not disable permissions.
Verify raw/Claude arms have no inherited user Skill, parent CLAUDE.md, plugin or
project setting that supplies Deep Native. Record all other customization consistently.

- **raw:** your selected DeepSeek model, standard host, no Deep Native.
- **skill:** exactly the same DeepSeek endpoint/model and host, with Deep Native.
- **claude:** a named, versioned native Claude model on its own intended endpoint.
  Do not leave the DeepSeek base URL active and accidentally benchmark a mapped alias.

For raw/native, ask: `Read TASK.md and complete its coding task.`
For skill, invoke: `/deep-native Read TASK.md and complete its coding task.`
That invocation is the treatment difference. Keep TASK.md itself identical. Capture
proof the Skill loaded; a prepared folder alone is insufficient.

Use the same wall-clock/turn/token ceilings, tools, repository permissions, dependency
versions and grading conditions. Pick these budgets before viewing results. Do not
let one arm silently use a larger context or more expensive reviewer model. Keep
API keys in local process memory/your existing secure mechanism; never send them in
chat or commit them. Do not publish raw logs until they are inspected for secrets.

The repository does not ship an unattended live-model runner in v0.1. This is deliberate:
it cannot safely infer your credentials, provider routing, CLI flags or spending budget.
Preparing fixtures and grading patches are automated; the live sessions are not.

## Grade after the agent stops

```bash
python3 evals/bench.py grade --workspace /tmp/dn-raw-01
python3 evals/bench.py grade --workspace /tmp/dn-skill-01
python3 evals/bench.py grade --workspace /tmp/dn-claude-01
```

The grader copies only `solution.py` into a temporary directory and supplies tests
from outside the agent workspace. Editing/removing the visible tests cannot replace
these tests. It records the candidate and grader hashes, pass/fail and timeout. It
returns `model_identity=NOT_ATTESTED`: the grader cannot establish who wrote a file.
Attach a separately audited model/session record before treating any grade as an
agent result. The full contract suite passes only when all 12 methods succeed.

**Not an adversarial sandbox.** Candidate Python executes on the machine. Use only
trusted patches, or run the grader inside a container/VM with no host credentials,
no sensitive mounts and network restrictions. Filesystem separation prevents accidental
grader edits, not malicious imports, reflection, process exits or forged test output.

## Record experiments without misleading numbers

For each run record task ID, initial hash, arm, exact provider/model identity, host
version, Skill commit, effective settings, seed if supported, repeat, budget, elapsed
time, token usage from the provider, grader outcome, interruptions and transcript
provenance. If costs are computed, record the pricing date and cache billing categories.
Do not assume subscription cost equals API price. Missing cost/token data stays missing.

Repeat at least several times in fresh workspaces and alternate/randomize arm order.
Report task-level success, confidence intervals, latency and cost per accepted task,
not only a single cherry-picked success. Predeclare timeouts and failures; do not drop
them after seeing an inconvenient result. A tiny sample has wide uncertainty.

Next, add 20+ diverse held-out repository tasks: bug repair, feature work, refactoring,
recovery after interruption and tool errors. Keep prompt tuning tasks separate from
the held-out set. Publish regressions as well as wins. Only then consider a claim
that the Skill improves a specified model on a specified workload.

## 中文速览

先用三个 `prepare` 命令创建相同起点，分别在真实 DeepSeek、相同 DeepSeek + Skill、明确版本的原生 Claude 中完成 TASK.md，再由 `grade` 检查产物。原生 Claude 组必须确认未继续经过 DeepSeek 兼容端点。未装 Hook 的实验不能写成 Hook 的效果。

评分器只证明提交代码是否通过测试，不证明作者是某个模型。三组需要独立会话、相同工具和预算、实际加载证据、重复实验。不要把这 12 个小测试当成模型能力基准，也不要把本仓库的工具测试数当成模型成功率。
