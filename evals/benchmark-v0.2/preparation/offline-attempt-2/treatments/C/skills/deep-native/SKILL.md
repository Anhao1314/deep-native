---
name: deep-native
description: Adaptive evidence-first coding behavior for DeepSeek in Claude Code. Use for repository investigation, bug fixing, feature work, refactors, verification, or interrupted coding tasks. Start with the lightest workflow that can safely solve the task; escalate only when evidence or risk requires it.
argument-hint: "<coding task>"
---

# Deep Native

Make the workflow more reliable without making every task heavier.

Task: $ARGUMENTS

Follow repository rules, user intent, and existing tool permissions. Deep Native does
not increase model intelligence, unlock tools, or prove parity with Claude. Prefer
useful work over ceremony.

## Route first

Choose the lightest mode that fits the observed task.

### FAST

Use FAST when the change is localized, acceptance is clear, risk is low, and there
has not been a failed attempt.

Workflow:

```text
inspect relevant code -> edit -> focused check -> deliver
```

Do not create Deep Native state, configure a persistent check contract, checkpoint,
or call the evidence runtime just to satisfy the Skill. A tiny task should stay tiny.

### STANDARD

Use STANDARD when the task crosses files, root cause is uncertain, or the first
attempt/check failed.

Workflow:

```text
inspect -> reproduce -> state one testable hypothesis -> edit
        -> focused check -> relevant broader check -> deliver
```

Do not start the persistent runtime by default. If the first hypothesis fails,
classify the failure before another edit.

### DEEP

Escalate to DEEP when any of these becomes true:

- two ineffective attempts have occurred;
- scope becomes repo-wide or spans multiple subsystems;
- interruption/compaction is likely;
- work is long-running;
- the change is high-risk or hard to roll back.

DEEP uses the persistent evidence runtime and checkpoint/recovery flow.

The rules above are authoritative. `scripts/policy.py` mirrors them for tests,
benchmarking, and genuinely ambiguous routing; normal tasks do not need to call it.

Read [adaptive-runtime.md](references/adaptive-runtime.md) only when routing,
failure classification, or escalation is unclear.

## Inspect before editing

Read the relevant repository instructions, Git status, source, and tests. Preserve
unrelated changes. Distinguish observations from guesses.

For bugs, reproduce the behavior when practical. For features, identify the smallest
observable acceptance condition. Do not scan the whole repository when a narrow read
is enough.

## Classify failures before retrying

When a command or check fails, decide what failed:

- **implementation**: inspect the behavior and diff, then correct the smallest code area;
- **hypothesis**: stop editing, gather discriminating evidence, and form a new hypothesis;
- **contract**: re-read acceptance/tests; never weaken success criteria for green output;
- **environment**: fix invocation, writable paths, shell form, or sandbox assumptions
  before changing product code;
- **dependency**: inspect runtime/pins; repair if authorized, otherwise report blocker;
- **budget**: checkpoint confirmed facts and next action instead of rushing completion;
- **unknown**: gather one new observation; do not repeat an unchanged failing command.

A repeated ineffective attempt is an escalation signal, not permission to retry forever.

## Verification is about fresh evidence

Run the smallest meaningful check first. Expand verification only as required by
the change and repository risk.

A passing check does not survive a relevant source/test change. If code changes after
the latest meaningful check, run fresh verification before claiming completion.

Do not treat version/help commands, blocked commands, process launch messages, or an
empty exit-zero command as proof that the feature works.

## DEEP runtime

For DEEP tasks, inspect the real project check commands and configure the evidence
runtime. Never replace another active task.

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/deep_native.py" --project "<repo-root>" status
python3 "${CLAUDE_SKILL_DIR}/scripts/deep_native.py" --project "<repo-root>" configure --name tests -- <real test argv>
python3 "${CLAUDE_SKILL_DIR}/scripts/deep_native.py" --project "<repo-root>" begin --session "${CLAUDE_SESSION_ID}" --goal "<acceptance condition>"
```

The test command is project-specific. Do not use the example from documentation if it
does not match the repository.

Checkpoint only meaningful state, not a transcript:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/deep_native.py" --project "<repo-root>" checkpoint \
  --note "<confirmed facts; current hypothesis; changed files>" \
  --next "<single concrete next action>"
```

Before completion:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/deep_native.py" --project "<repo-root>" verify --timeout 60
python3 "${CLAUDE_SKILL_DIR}/scripts/deep_native.py" --project "<repo-root>" finish \
  --summary "<what changed>" --risk "<remaining limitation or not-tested area>"
```

If tools, credentials, dependencies, or budget prevent verification, use
`block --reason "<specific blocker>"`. A blocker is not success.

Read [recovery.md](references/recovery.md) only for actual recovery/compaction.
Read [verification.md](references/verification.md) when check coverage or evidence
freshness is material.

## Deliver

Always finish with a user-facing result when the host still has budget. Report:

1. what changed or what was found;
2. checks actually executed and their observed outcomes;
3. remaining risk or blocker.

Do not invent test counts, claim a command ran when it did not, or confuse a Skill
instruction with independent evidence. Keep FAST answers short, STANDARD answers
focused, and DEEP answers evidence-rich.
