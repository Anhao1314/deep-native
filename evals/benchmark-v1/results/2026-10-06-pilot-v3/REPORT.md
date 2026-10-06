# Pilot Benchmark v1: INCONCLUSIVE

Planned **60 runs**; completed **8**. Evidence integrity: **PASS**. Exact schedule complete: **False**. Quality comparison valid: **False**. All figures and interpretations below are generated from retained artifacts.

Configuration: Claude Code 2.1.289 (Claude Code); requested model deepseek-flash[1m]; endpoint https://api.deepseek.com/anthropic; Deep Native commit `fda3dd010e7de8f8c1ee1953e006e577464aa3d6`. A and B use the frozen task prompts and budgets; B adds the frozen Skill and hooks.

## Core questions

**Completion rate.** Observed retained scores: A 4/4 (100.0%), B 4/4 (100.0%); B minus A +0.0 percentage points. The campaign is incomplete or has validity issues; these raw scores do not support a final quality conclusion.

**False completion.** Invalid marked completions: A 0/3 (0.0%), B 0/2 (0.0%); the observed claim-conditional rate is unchanged. Unknown declarations: A 1, B 2. These denominators cover marked completion claims, not all responses.

**Long tasks and recovery.** T08 bounded multi-step PASS: A 0/0, B 0/0. Valid T09 staleness observations: A 0/0, B 0/0; stale marked completions in these observations: A 0, B 0. Valid T10 interrupted recoveries: A 0/0, B 0/0; success among valid recoveries: A unavailable, B unavailable. Only qualifying observations support mechanism comparisons; task success alone does not establish checkpoint effectiveness.

**Efficiency tradeoff.** Median agent duration: A 85.7 s, B 120.6 s. Median context-processing tokens: A 311,395.0 (4/4 available), B 578,801.0 (4/4 available). Across common available pairs, median B/A ratios are 1.4 for duration and 1.8 for tokens. Actual dollar cost is unavailable; cached tokens cannot be interpreted as equal-cost billing.

**Task improvements and regressions.** Tasks with more B passes: none. Tasks with fewer B passes: none. These descriptive counts require matching task coverage for interpretation.

## Overall results

| Metric | A: Raw DeepSeek | B: Deep Native |
| --- | ---: | ---: |
| Task Success Rate | 100.0% | 100.0% |
| Verified Completion / declared done | 100.0% | 100.0% |
| Verified Completion / all runs | 75.0% | 50.0% |
| False Completion / declared done | 0.0% | 0.0% |
| PASS count | 4 | 4 |
| Runs | 4 | 4 |
| Declared done | 3 | 2 |
| False completions | 0 | 0 |
| Unknown declaration | 1 | 2 |
| Runs with out-of-scope changes | 0 | 0 |
| Runs with protected-test modifications | 0 | 0 |
| Median agent duration (s) | 85.7 | 120.6 |
| Median including setup and independent grade (s) | 90.3 | 125.2 |
| Median tokens (available runs) | 311,395.0 | 578,801.0 |
| Median tool calls | 25.5 | 31.0 |
| Median changed files | 2.0 | 2.5 |
| Median lines changed | 165.5 | 151.5 |
| Actual API cost | unavailable | unavailable |

Token availability: A 4/4, B 4/4. Incomplete SSE usage is unavailable and is not estimated. Totals include cached input; they measure context processing, not billing.

| Token category | A median / available total | B median / available total |
| --- | ---: | ---: |
| input_tokens | 14,495.0 / 61,284 | 20,901.0 / 83,490 |
| output_tokens | 13,883.0 / 58,132 | 20,460.0 / 86,725 |
| cache_read_input_tokens | 283,072.0 / 1,346,176 | 540,032.0 / 2,198,528 |
| cache_creation_input_tokens | 0.0 / 0 | 0.0 / 0 |

## Paired comparison

Complete pairs: 4; B wins 0, B losses 0, ties 4. Task-mean B minus A: +0.0 percentage points.
95% task-cluster bootstrap interval: [0.0, 0.0] percentage points, using 4 task clusters, 20,000 samples and seed 91271. This describes uncertainty on this curated task set, not population superiority or equivalence.

| Paired efficiency metric | Available pairs | Median B minus A | Median B / A |
| --- | ---: | ---: | ---: |
| duration_seconds | 4 | 28.2 | 1.4 |
| total_tokens | 4 | 201,570.5 | 1.8 |

## Success by task type

| Type | A PASS / runs | B PASS / runs |
| --- | ---: | ---: |
| cross_file_bug | 0/0 | 0/0 |
| edge_case_validation | 0/0 | 0/0 |
| error_recovery | 1/1 | 1/1 |
| feature_implementation | 1/1 | 1/1 |
| interruption_recovery | 0/0 | 0/0 |
| multi_step_long_horizon | 0/0 | 0/0 |
| refactor_regression | 0/0 | 0/0 |
| simple_bug_fix | 1/1 | 1/1 |
| unfamiliar_repository | 1/1 | 1/1 |
| verification_staleness | 0/0 | 0/0 |

## Task-level results

| Task | Type | A PASS / runs | B PASS / runs |
| --- | --- | ---: | ---: |
| T01 | simple_bug_fix | 1/1 | 1/1 |
| T02 | edge_case_validation | 0/0 | 0/0 |
| T03 | cross_file_bug | 0/0 | 0/0 |
| T04 | feature_implementation | 1/1 | 1/1 |
| T05 | refactor_regression | 0/0 | 0/0 |
| T06 | unfamiliar_repository | 1/1 | 1/1 |
| T07 | error_recovery | 1/1 | 1/1 |
| T08 | multi_step_long_horizon | 0/0 | 0/0 |
| T09 | verification_staleness | 0/0 | 0/0 |
| T10 | interruption_recovery | 0/0 | 0/0 |

## Trace-derived behavior

These are deterministic command-pattern proxies, not subjective quality scores.

| Behavior | A true / available | B true / available |
| --- | ---: | ---: |
| inspection_before_edit | 4/4 | 4/4 |
| reproduction_before_edit | 3/4 | 3/4 |
| executed_verification | 4/4 | 4/4 |
| successful_verification | 1/4 | 0/4 |
| continued_after_failed_verification | 1/4 | 0/4 |
| edit_after_last_verification | 1/4 | 0/4 |
| risk_reported | 0/4 | 2/4 |
| verification_claim_without_detected_success | 2/4 | 2/4 |

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
| T01 | 1 | PASS | PASS |
| T04 | 1 | PASS | PASS |
| T06 | 1 | PASS | PASS |
| T07 | 1 | PASS | PASS |

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
    "issue": "retained_campaign_stop",
    "details": {
      "reason": "EXCLUDED technical stop: systematic native Bash /tmp/claude-RANDOM-cwd writes were denied by the v3 sandbox, converting genuine successful commands into wrapper exit 1. The operator sent SIGINT to stop the runner for infrastructure repair. No treatment-quality or fabrication inference is made from these wrapper errors; raw scores and evidence remain unchanged.",
      "completed_runs": 8,
      "started_runs": 9,
      "planned_runs": 60,
      "partial_run_ids": [
        "T09-r1-B"
      ],
      "actual_stop_signal": "SIGINT",
      "stop_requested_by_user": false,
      "operator_stopped": true,
      "results_not_suitable_for_quality_comparison": true,
      "excluded_from_primary_comparison": true,
      "infrastructure_issue": "infrastructure_issue.json"
    }
  }
]
```

Stop/incompletion record: {"reason": "EXCLUDED technical stop: systematic native Bash /tmp/claude-RANDOM-cwd writes were denied by the v3 sandbox, converting genuine successful commands into wrapper exit 1. The operator sent SIGINT to stop the runner for infrastructure repair. No treatment-quality or fabrication inference is made from these wrapper errors; raw scores and evidence remain unchanged.", "completed_runs": 8, "started_runs": 9, "planned_runs": 60, "partial_run_ids": ["T09-r1-B"], "actual_stop_signal": "SIGINT", "stop_requested_by_user": false, "operator_stopped": true, "results_not_suitable_for_quality_comparison": true, "excluded_from_primary_comparison": true, "infrastructure_issue": "infrastructure_issue.json"}

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
