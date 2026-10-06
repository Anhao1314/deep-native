# Architecture and boundaries

Deep Native is deliberately split into an **adaptive behavior policy** and a
**deterministic evidence runtime**.

```text
User task + repository rules
            |
     Claude Code + model
            |
   adaptive Skill policy
      /      |       \
   FAST   STANDARD   DEEP
    |         |        |
 normal     normal   persistent
 tools       tools     runtime
    \         |        /
       meaningful checks
              |
       user-facing result
```

The v0.1 live pilot showed that mandatory ceremony changed agent behavior but did not
improve task success in the retained matched sample. v0.2 Candidate therefore defaults
to the smallest useful workflow and escalates only when risk/evidence demands it.

## FAST

Localized task, clear acceptance, low risk, no failed attempt.

```text
inspect -> edit -> focused check -> deliver
```

No Deep Native state or persistent lifecycle is required.

## STANDARD

Cross-file work, uncertain root cause, or the first failed attempt.

```text
inspect -> reproduce -> hypothesis -> edit
        -> focused check -> broader relevant check -> deliver
```

A failed attempt must be classified before another edit. Persistent state is still
optional.

## DEEP

Triggered by two ineffective attempts, repo-wide/multi-subsystem scope,
long-running/high-risk work, or interruption/compaction risk.

```text
inspect -> reproduce -> classify -> begin
        -> checkpoint* -> verify -> review -> finish
```

Only DEEP requires the existing task/checkpoint evidence runtime.

## Policy mirror

`skills/deep-native/scripts/policy.py` is a deterministic, stateless mirror of the
routing and failure-classification rules. It is intended for tests, evals, and ambiguous
routing. It is not another mandatory tool call for normal tasks.

## Evidence runtime

The existing helper remains the enforcement layer for DEEP tasks:

`configure -> begin(active) -> checkpoint* -> verify -> finish(complete)`

An unsuccessful or interrupted verify does not complete the task. Every verification
invalidates the previous current attempt before running checks. `finish` checks the
latest receipt, frozen check identities, configuration hash, and current source
fingerprint. `block(reason)` ends the task as blocked, not complete.

A passing receipt proves only that configured checks exited successfully against the
recorded worktree. It does not prove the checks were sufficient, and it is not a
cryptographic attestation.

## Failure classification

The Skill distinguishes implementation, hypothesis, contract, environment, dependency,
budget, and unknown failures. This matters because the v0.1 pilot recorded sandbox temp
file denials: an environment failure should change the invocation or writable path,
not trigger product-code edits.

## Freshness

All modes follow one rule: a meaningful check is evidence only for the code it actually
checked. Relevant source/test changes after a passing check require fresh verification
before completion. Version/help commands and blocked commands do not count as functional
verification.

## Hooks and recovery

SessionStart and Stop hooks remain optional and are primarily useful for DEEP tasks.
Checkpoint state is recovery data, not a conversation transcript and not proof that old
claims were correct. Parallel work should use separate Git worktrees.

## Evaluation separation

The heavy 21-run v0.1 pilot remains on the `benchmark-v1` branch so raw artifacts do
not bloat the product branch. Mainline documentation imports only measured conclusions.
The next live experiment is a small mechanism-level ablation before any larger benchmark.
