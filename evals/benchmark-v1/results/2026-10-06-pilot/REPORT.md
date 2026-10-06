# Pilot Benchmark v1: INCONCLUSIVE

Planned **60 runs**; completed **2**. Evidence integrity: **PASS**. Exact schedule complete: **False**. Quality comparison valid: **False**. All figures and interpretations below are generated from retained artifacts.

Configuration: Claude Code 2.1.289 (Claude Code); requested model deepseek-flash[1m]; endpoint https://api.deepseek.com/anthropic; Deep Native commit `fda3dd010e7de8f8c1ee1953e006e577464aa3d6`. A and B use the frozen task prompts and budgets; B adds the frozen Skill and hooks.

## Core questions

**Completion rate.** Observed retained scores: A 1/1 (100.0%), B 1/1 (100.0%); B minus A +0.0 percentage points. The campaign is incomplete or has validity issues; these raw scores do not support a final quality conclusion.

**False completion.** Invalid marked completions: A 0/1 (0.0%), B 0/0 (unavailable); the observed claim-conditional rate is unavailable. Unknown declarations: A 0, B 1. These denominators cover marked completion claims, not all responses.

**Long tasks and recovery.** T08 bounded multi-step PASS: A 0/0, B 0/0. Valid T09 staleness observations: A 0/0, B 0/0; stale marked completions in these observations: A 0, B 0. Valid T10 interrupted recoveries: A 0/0, B 0/0; success among valid recoveries: A unavailable, B unavailable. Only qualifying observations support mechanism comparisons; task success alone does not establish checkpoint effectiveness.

**Efficiency tradeoff.** Median agent duration: A 291.5 s, B 247.2 s. Median context-processing tokens: A 678,574.0 (1/1 available), B 658,958.0 (1/1 available). Across common available pairs, median B/A ratios are 0.8 for duration and 1.0 for tokens. Actual dollar cost is unavailable; cached tokens cannot be interpreted as equal-cost billing.

**Task improvements and regressions.** Tasks with more B passes: none. Tasks with fewer B passes: none. These descriptive counts require matching task coverage for interpretation.

## Overall results

| Metric | A: Raw DeepSeek | B: Deep Native |
| --- | ---: | ---: |
| Task Success Rate | 100.0% | 100.0% |
| Verified Completion / declared done | 100.0% | unavailable |
| Verified Completion / all runs | 100.0% | 0.0% |
| False Completion / declared done | 0.0% | unavailable |
| PASS count | 1 | 1 |
| Runs | 1 | 1 |
| Declared done | 1 | 0 |
| False completions | 0 | 0 |
| Unknown declaration | 0 | 1 |
| Runs with out-of-scope changes | 0 | 0 |
| Runs with protected-test modifications | 0 | 0 |
| Median agent duration (s) | 291.5 | 247.2 |
| Median including setup and independent grade (s) | 292.1 | 247.8 |
| Median tokens (available runs) | 678,574.0 | 658,958.0 |
| Median tool calls | 28.0 | 28.0 |
| Median changed files | 2.0 | 2.0 |
| Median lines changed | 262.0 | 250.0 |
| Actual API cost | unavailable | unavailable |

Token availability: A 1/1, B 1/1. Incomplete SSE usage is unavailable and is not estimated. Totals include cached input; they measure context processing, not billing.

| Token category | A median / available total | B median / available total |
| --- | ---: | ---: |
| input_tokens | 18,658.0 / 18,658 | 21,396.0 / 21,396 |
| output_tokens | 26,700.0 / 26,700 | 23,162.0 / 23,162 |
| cache_read_input_tokens | 633,216.0 / 633,216 | 614,400.0 / 614,400 |
| cache_creation_input_tokens | 0.0 / 0 | 0.0 / 0 |

## Paired comparison

Complete pairs: 1; B wins 0, B losses 0, ties 1. Task-mean B minus A: +0.0 percentage points.

| Paired efficiency metric | Available pairs | Median B minus A | Median B / A |
| --- | ---: | ---: | ---: |
| duration_seconds | 1 | -44.3 | 0.8 |
| total_tokens | 1 | -19,616.0 | 1.0 |

## Success by task type

| Type | A PASS / runs | B PASS / runs |
| --- | ---: | ---: |
| cross_file_bug | 0/0 | 0/0 |
| edge_case_validation | 0/0 | 0/0 |
| error_recovery | 0/0 | 0/0 |
| feature_implementation | 1/1 | 1/1 |
| interruption_recovery | 0/0 | 0/0 |
| multi_step_long_horizon | 0/0 | 0/0 |
| refactor_regression | 0/0 | 0/0 |
| simple_bug_fix | 0/0 | 0/0 |
| unfamiliar_repository | 0/0 | 0/0 |
| verification_staleness | 0/0 | 0/0 |

## Task-level results

| Task | Type | A PASS / runs | B PASS / runs |
| --- | --- | ---: | ---: |
| T01 | simple_bug_fix | 0/0 | 0/0 |
| T02 | edge_case_validation | 0/0 | 0/0 |
| T03 | cross_file_bug | 0/0 | 0/0 |
| T04 | feature_implementation | 1/1 | 1/1 |
| T05 | refactor_regression | 0/0 | 0/0 |
| T06 | unfamiliar_repository | 0/0 | 0/0 |
| T07 | error_recovery | 0/0 | 0/0 |
| T08 | multi_step_long_horizon | 0/0 | 0/0 |
| T09 | verification_staleness | 0/0 | 0/0 |
| T10 | interruption_recovery | 0/0 | 0/0 |

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

Risk reporting records explicit risk/limitation language, not the completeness of disclosure. Continued-after-failure records a later detected successful verification. Unsupported verification language is a trace flag; fabricated execution claims remain unavailable without trace review. Source-edit and stale-verification flags are warnings, not independent proof of fabrication.

## Actual staleness and recovery interventions

A valid T09 observation requires independently passing phase 1, a detected successful agent verification in phase 1, and an actual later source change. Legacy missing fields are unavailable. A valid T10 observation requires actual SIGKILL interruption, two distinct session IDs, the same frozen budget configuration, and observed assistant turns within the shared ceiling. All final strict task scores still include nonqualifying runs.

```json
{
  "A": {
    "multi_step_long_horizon": {
      "runs": 0,
      "passes": 0
    },
    "staleness": {
      "runs": 0,
      "observation_fields_available": 0,
      "observation_fields_unavailable": 0,
      "stage1_independently_passed": 0,
      "valid_observations": 0,
      "actual_later_source_changes": 0,
      "stale_completion_claims_valid_observations": 0,
      "stale_completion_claim_rate_valid_observations": null,
      "valid_observation_final_passes": 0,
      "final_passes": 0
    },
    "recovery": {
      "runs": 0,
      "observation_fields_available": 0,
      "actual_interruptions": 0,
      "valid_observations": 0,
      "state_at_interrupt_valid_observations": 0,
      "checkpoint_notes_valid_observations": 0,
      "valid_observation_passes": 0,
      "valid_observation_success_rate": null,
      "passes": 0
    }
  },
  "B": {
    "multi_step_long_horizon": {
      "runs": 0,
      "passes": 0
    },
    "staleness": {
      "runs": 0,
      "observation_fields_available": 0,
      "observation_fields_unavailable": 0,
      "stage1_independently_passed": 0,
      "valid_observations": 0,
      "actual_later_source_changes": 0,
      "stale_completion_claims_valid_observations": 0,
      "stale_completion_claim_rate_valid_observations": null,
      "valid_observation_final_passes": 0,
      "final_passes": 0
    },
    "recovery": {
      "runs": 0,
      "observation_fields_available": 0,
      "actual_interruptions": 0,
      "valid_observations": 0,
      "state_at_interrupt_valid_observations": 0,
      "checkpoint_notes_valid_observations": 0,
      "valid_observation_passes": 0,
      "valid_observation_success_rate": null,
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

Strict PASS requires independent contracts, upstream regressions, intact protected tests and an allowed modification scope. Verified completion uses explicit STATUS declarations; missing declarations are unknown. Frozen run scores are never relabelled by this analysis.

The frozen judgment rule is PASS with a positive task-cluster interval, FAIL with a negative interval or identical outcomes in all 30 pairs after a valid complete 60-run campaign, and INCONCLUSIVE otherwise. A FAIL for identical pairs means no observed improvement here; it does not prove population equivalence. Evidence problems, stop records or scoring-contract defects force INCONCLUSIVE.

## Validity and provenance

- [Evidence integrity audit](evidence_audit.json): exact schedule coverage, identities, retained hashes and grade/usage/session cross-checks.
- [Frozen protocol and treatment hashes](freeze.json), [environment](audit.json), [baselines](baselines.json), [immutable tasks](tasks.json), [random schedule](schedule.json).

Retained validity issues:
```json
[
  {
    "issue": "frozen_treatment_hash_unavailable"
  },
  {
    "issue": "retained_campaign_stop",
    "details": {
      "reason": "Stopped and excluded whole initial campaign after discovering Claude background children can have a different process group. Runner must terminate descendants as well as the launcher process group before actual recovery tests. No Deep Native or task changes. All artifacts retained; full replacement campaign restarts same schedule.",
      "completed_runs": 2,
      "started_runs": 3,
      "excluded_from_primary_results": true
    }
  }
]
```

Stop/incompletion record: {"reason": "Stopped and excluded whole initial campaign after discovering Claude background children can have a different process group. Runner must terminate descendants as well as the launcher process group before actual recovery tests. No Deep Native or task changes. All artifacts retained; full replacement campaign restarts same schedule.", "completed_runs": 2, "started_runs": 3, "excluded_from_primary_results": true}

## Limitations

- Ten curated tasks on two Python utility repositories, not a representative coding-task population.
- Three tasks use injected regressions; one task injects a transient infrastructure failure.
- Long-horizon task is bounded to 24 assistant turns and 480 seconds, not a multi-hour project.
- Provider model alias is mutable; response identity is recorded but underlying weights are not attestable.
- Seatbelt is a pragmatic local boundary, not a hostile-agent containment proof.
- Provider-side prompt caching cannot be reset; randomized pairs reduce, but do not eliminate, time/cache effects.
- Trace-pattern behavior metrics are proxies; risk completeness and fabricated checks require trace review.
- Wilson intervals treat runs as independent and are descriptive only; task-cluster bootstrap is the primary uncertainty estimate.
- API dollar cost is unavailable. CLI costUSD with costBasis unknown is retained only as raw diagnostic telemetry.
- Token totals include cached input and measure context processing, not dollar billing; missing usage is not estimated.
- Mechanism outcomes require actual qualifying interventions; zero valid observations cannot establish effectiveness.

## Evidence and reproduction

- [Machine-readable summary](summary.json), [all results](results.jsonl), [CSV](results.csv), [observed success chart](success.svg).
- Every runs/<id>/ retains prompts, transcripts, tool events, API usage, independent grades, response, patch and artifact hashes.
- Regenerate: `python3 evals/benchmark-v1/harness.py analyze --output <campaign-directory>`.
- Live execution commands and dependency/isolation details: [benchmark README](../../README.md).
