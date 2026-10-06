# Pilot Benchmark v1: INCONCLUSIVE

Planned **60 runs**; completed **2**. All figures below are generated from retained artifacts.

| Metric | A: Raw DeepSeek | B: Deep Native |
| --- | ---: | ---: |
| Task Success Rate | 100.0% | 100.0% |
| Verified Completion / declared done | 100.0% | unavailable |
| Verified Completion / all runs | 100.0% | 0.0% |
| PASS / runs | 1 | 1 |
| Declared done | 1 | 0 |
| False completions | 0 | 0 |
| Unknown declaration | 0 | 1 |
| Median duration (s) | 291.5 | 247.2 |
| Median tokens (available runs) | 678,574.0 | 658,958.0 |
| Median tool calls | 28.0 | 28.0 |
| Median changed files | 2.0 | 2.0 |
| Median lines changed | 262.0 | 250.0 |
| Actual API cost | unavailable | unavailable |

Token availability: A 1/1, B 1/1. Incomplete interrupted SSE responses are not estimated.

Paired complete observations: 1. Task-mean change: 0.0% percentage-point scale.

## Task-level results

| Task | Type | A PASS / runs | B PASS / runs |
| --- | --- | ---: | ---: |
| T04 | feature_implementation | 1/1 | 1/1 |

## Trace-derived behavior

These are deterministic command-pattern proxies, not subjective quality scores.

| Behavior | A true / available | B true / available |
| --- | ---: | ---: |
| inspection_before_edit | 1/1 | 1/1 |
| reproduction_before_edit | 0/1 | 0/1 |
| executed_verification | 1/1 | 1/1 |
| successful_verification | 1/1 | 1/1 |
| continued_after_failed_verification | 1/1 | 0/0 |
| edit_after_last_verification | 0/1 | 0/1 |
| risk_reported | 0/1 | 0/1 |
| verification_claim_without_detected_success | 0/1 | 0/1 |

Risk reporting means explicit risk/limitation language occurred in the final response; it does not assess whether the risk disclosure was complete. Unsupported verification language is a trace-pattern flag; fabricated execution claims remain unavailable without human trace review. `edit_after_last_verification` is a warning proxy, not proof of a false claim.

## Actual staleness and recovery interventions

```json
{
  "A": {
    "staleness": {
      "runs": 0,
      "stage1_independently_passed": 0,
      "actual_later_source_changes": 0,
      "stale_completion_claims": 0,
      "final_passes": 0
    },
    "recovery": {
      "runs": 0,
      "actual_interruptions": 0,
      "new_sessions": 0,
      "state_at_interrupt": 0,
      "checkpoint_notes_at_interrupt": 0,
      "passes": 0
    }
  },
  "B": {
    "staleness": {
      "runs": 0,
      "stage1_independently_passed": 0,
      "actual_later_source_changes": 0,
      "stale_completion_claims": 0,
      "final_passes": 0
    },
    "recovery": {
      "runs": 0,
      "actual_interruptions": 0,
      "new_sessions": 0,
      "state_at_interrupt": 0,
      "checkpoint_notes_at_interrupt": 0,
      "passes": 0
    }
  }
}
```

## Paired results

| Task | Repeat | A | B |
| --- | ---: | --- | --- |
| T04 | 1 | PASS | PASS |

## Failures

| Run | Classification | Evidence |
| --- | --- | --- |

## Interpretation

A strict PASS requires independent contract checks, upstream regression tests, preserved protected tests, and an allowed modification scope. A completion claim is measured by the common `STATUS: DONE` marker; missing markers are unknown.

The frozen judgment rule is PASS only with a positive task-cluster interval, FAIL with a negative interval or no differences in any pair after all 60 runs, and INCONCLUSIVE otherwise. Protocol violations force INCONCLUSIVE.

For recovery, inspect actual SIGKILL records and distinct session IDs; do not infer checkpoint effectiveness merely from task success. For staleness, inspect phase1 verification and the subsequent source change before attributing an improvement.

## Limitations

- Ten curated tasks on two Python utility repositories, not a representative coding-task population.
- Three tasks use injected regressions; one task injects a transient infrastructure failure.
- Long-horizon task is bounded to 24 assistant turns and 480 seconds, not a multi-hour project.
- Provider model alias is mutable; response identity is recorded but underlying weights are not attestable.
- Seatbelt is a pragmatic local boundary, not a hostile-agent containment proof.
- Provider-side prompt caching cannot be reset; randomized pairs reduce, but do not eliminate, time/cache effects.
- Regex-derived behavior metrics are proxies; risk reporting and fabricated checks require human trace review.
- Wilson intervals treat runs as independent and are descriptive only; task-cluster bootstrap is the primary uncertainty estimate.
- API dollar cost is unavailable. CLI costUSD with costBasis unknown is retained only as raw diagnostic telemetry.

Stop/incompletion record: {"reason": "Stopped and excluded whole initial campaign after discovering Claude background children can have a different process group. Runner must terminate descendants as well as the launcher process group before actual recovery tests. No Deep Native or task changes. All artifacts retained; full replacement campaign restarts same schedule.", "completed_runs": 2, "started_runs": 3, "excluded_from_primary_results": true}

## Evidence and reproduction

- [Environment audit](audit.json), [frozen protocol](freeze.json), [tasks](tasks.json), [random schedule](schedule.json).
- [Machine-readable summary](summary.json), [all results](results.jsonl), [CSV](results.csv).
- Each `runs/<id>/` retains exact prompts, transcripts, tool events, API usage, baseline/independent grades, final response, patch, and artifact hashes.
- Regenerate: `python3 evals/benchmark-v1/harness.py analyze --output <campaign-directory>`.
- Real live execution commands and dependency/isolation details: [benchmark README](../../README.md).
