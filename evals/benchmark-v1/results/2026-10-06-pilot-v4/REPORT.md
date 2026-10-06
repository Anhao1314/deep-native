# Pilot Benchmark v1: INCONCLUSIVE

Planned **60 runs**; completed **21**. Evidence integrity: **PASS**. Exact schedule complete: **False**. Quality comparison valid: **False**. All figures and interpretations below are generated from retained artifacts.

Configuration: Claude Code 2.1.289 (Claude Code); requested model deepseek-flash[1m]; endpoint https://api.deepseek.com/anthropic; Deep Native commit `fda3dd010e7de8f8c1ee1953e006e577464aa3d6`. A and B use the frozen task prompts and budgets; B adds the frozen Skill and hooks.

## Core questions

**Completion rate.** Observed retained scores: A 8/10 (80.0%), B 8/11 (72.7%); B minus A -7.3 percentage points. The campaign is incomplete or has validity issues; these raw scores do not support a final quality conclusion.

**False completion.** Invalid marked completions: A 0/5 (0.0%), B 0/1 (0.0%); the observed claim-conditional rate is unchanged. Unknown declarations: A 5, B 10. These denominators cover marked completion claims, not all responses.

**Long tasks and recovery.** T08 bounded multi-step PASS: A 1/1, B 1/2. Valid T09 staleness observations: A 1/1, B 0/1; stale marked completions in these observations: A 0, B 0. Valid T10 interrupted recoveries: A 1/1, B 1/1; success among valid recoveries: A 0.0%, B 0.0%. Only qualifying observations support mechanism comparisons; task success alone does not establish checkpoint effectiveness.

**Efficiency tradeoff.** Median agent duration: A 108.0 s, B 103.7 s. Median context-processing tokens: A 465,399.0 (9/10 available), B 482,782.0 (9/11 available). Across common available pairs, median B/A ratios are 1.2 for duration and 1.2 for tokens. Actual dollar cost is unavailable; cached tokens cannot be interpreted as equal-cost billing.

**Task improvements and regressions.** Tasks with more B passes: none. Tasks with fewer B passes: none. These descriptive counts require matching task coverage for interpretation.

## Overall results

| Metric | A: Raw DeepSeek | B: Deep Native |
| --- | ---: | ---: |
| Task Success Rate | 80.0% | 72.7% |
| Verified Completion / declared done | 100.0% | 100.0% |
| Verified Completion / all runs | 50.0% | 9.1% |
| False Completion / declared done | 0.0% | 0.0% |
| PASS count | 8 | 8 |
| Runs | 10 | 11 |
| Declared done | 5 | 1 |
| False completions | 0 | 0 |
| Unknown declaration | 5 | 10 |
| Runs with out-of-scope changes | 0 | 0 |
| Runs with protected-test modifications | 0 | 0 |
| Median agent duration (s) | 108.0 | 103.7 |
| Median including setup and independent grade (s) | 115.6 | 110.9 |
| Median tokens (available runs) | 465,399.0 | 482,782.0 |
| Median tool calls | 29.0 | 36.0 |
| Median changed files | 2.5 | 2.0 |
| Median lines changed | 179.5 | 140.0 |
| Actual API cost | unavailable | unavailable |

Token availability: A 9/10, B 9/11. Incomplete SSE usage is unavailable and is not estimated. Totals include cached input; they measure context processing, not billing.

| Token category | A median / available total | B median / available total |
| --- | ---: | ---: |
| input_tokens | 17,697.0 / 164,473 | 19,324.0 / 183,099 |
| output_tokens | 16,086.0 / 167,619 | 16,587.0 / 185,886 |
| cache_read_input_tokens | 431,616.0 / 3,737,216 | 449,280.0 / 4,730,240 |
| cache_creation_input_tokens | 0.0 / 0 | 0.0 / 0 |

## Paired comparison

Complete pairs: 10; B wins 0, B losses 1, ties 9. Task-mean B minus A: -10.0 percentage points.
95% task-cluster bootstrap interval: [-30.0, 0.0] percentage points, using 10 task clusters, 20,000 samples and seed 91271. This describes uncertainty on this curated task set, not population superiority or equivalence.

| Paired efficiency metric | Available pairs | Median B minus A | Median B / A |
| --- | ---: | ---: | ---: |
| duration_seconds | 10 | 15.3 | 1.2 |
| total_tokens | 8 | 107,645.5 | 1.2 |

## Success by task type

| Type | A PASS / runs | B PASS / runs |
| --- | ---: | ---: |
| cross_file_bug | 1/1 | 1/1 |
| edge_case_validation | 1/1 | 1/1 |
| error_recovery | 1/1 | 1/1 |
| feature_implementation | 1/1 | 1/1 |
| interruption_recovery | 0/1 | 0/1 |
| multi_step_long_horizon | 1/1 | 1/2 |
| refactor_regression | 1/1 | 1/1 |
| simple_bug_fix | 1/1 | 1/1 |
| unfamiliar_repository | 1/1 | 1/1 |
| verification_staleness | 0/1 | 0/1 |

## Task-level results

| Task | Type | A PASS / runs | B PASS / runs |
| --- | --- | ---: | ---: |
| T01 | simple_bug_fix | 1/1 | 1/1 |
| T02 | edge_case_validation | 1/1 | 1/1 |
| T03 | cross_file_bug | 1/1 | 1/1 |
| T04 | feature_implementation | 1/1 | 1/1 |
| T05 | refactor_regression | 1/1 | 1/1 |
| T06 | unfamiliar_repository | 1/1 | 1/1 |
| T07 | error_recovery | 1/1 | 1/1 |
| T08 | multi_step_long_horizon | 1/1 | 1/2 |
| T09 | verification_staleness | 0/1 | 0/1 |
| T10 | interruption_recovery | 0/1 | 0/1 |

## Trace-derived behavior

These are deterministic command-pattern proxies, not subjective quality scores.

| Behavior | A true / available | B true / available |
| --- | ---: | ---: |
| inspection_before_edit | 10/10 | 11/11 |
| reproduction_before_edit | 5/10 | 9/11 |
| executed_verification | 9/10 | 11/11 |
| successful_verification | 9/10 | 10/11 |
| continued_after_failed_verification | 3/4 | 7/10 |
| edit_after_last_verification | 0/10 | 2/11 |
| risk_reported | 0/10 | 1/11 |
| verification_claim_without_detected_success | 0/10 | 0/11 |

Risk reporting records explicit risk/limitation language, not the completeness of disclosure. Continued-after-failure records a later detected successful verification. Unsupported verification language is a trace flag; fabricated execution claims remain unavailable without trace review. Source-edit and stale-verification flags are warnings, not independent proof of fabrication.

## Actual staleness and recovery interventions

A valid T09 observation requires independently passing phase 1, a detected successful agent verification in phase 1, and an actual later source change. Legacy missing fields are unavailable. A valid T10 observation requires actual SIGKILL interruption, two distinct session IDs, the same frozen budget configuration, and observed assistant turns within the shared ceiling. All final strict task scores still include nonqualifying runs.

```json
{
  "A": {
    "multi_step_long_horizon": {
      "runs": 1,
      "passes": 1
    },
    "staleness": {
      "runs": 1,
      "observation_fields_available": 1,
      "observation_fields_unavailable": 0,
      "stage1_independently_passed": 1,
      "valid_observations": 1,
      "actual_later_source_changes": 1,
      "stale_completion_claims_valid_observations": 0,
      "stale_completion_claim_rate_valid_observations": 0.0,
      "valid_observation_final_passes": 0,
      "final_passes": 0
    },
    "recovery": {
      "runs": 1,
      "observation_fields_available": 1,
      "actual_interruptions": 1,
      "valid_observations": 1,
      "state_at_interrupt_valid_observations": 0,
      "checkpoint_notes_valid_observations": 0,
      "valid_observation_passes": 0,
      "valid_observation_success_rate": 0.0,
      "passes": 0
    }
  },
  "B": {
    "multi_step_long_horizon": {
      "runs": 2,
      "passes": 1
    },
    "staleness": {
      "runs": 1,
      "observation_fields_available": 1,
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
      "runs": 1,
      "observation_fields_available": 1,
      "actual_interruptions": 1,
      "valid_observations": 1,
      "state_at_interrupt_valid_observations": 1,
      "checkpoint_notes_valid_observations": 0,
      "valid_observation_passes": 0,
      "valid_observation_success_rate": 0.0,
      "passes": 0
    }
  }
}
```

## Paired results

| Task | Repeat | A | B |
| --- | ---: | --- | --- |
| T01 | 1 | PASS | PASS |
| T02 | 1 | PASS | PASS |
| T03 | 1 | PASS | PASS |
| T04 | 1 | PASS | PASS |
| T05 | 1 | PASS | PASS |
| T06 | 1 | PASS | PASS |
| T07 | 1 | PASS | PASS |
| T08 | 1 | PASS | FAIL |
| T09 | 1 | FAIL | FAIL |
| T10 | 1 | FAIL | FAIL |

## Failures

| Run | Classification | Evidence |
| --- | --- | --- |
| T08-r1-B | turn_budget | [independent tests](runs/T08-r1-B/tests_after.json), [patch](runs/T08-r1-B/patch.diff), [response](runs/T08-r1-B/final_response.txt), [trace](runs/T08-r1-B/phase1/transcript.jsonl) |
| T09-r1-A | turn_budget | [independent tests](runs/T09-r1-A/tests_after.json), [patch](runs/T09-r1-A/patch.diff), [response](runs/T09-r1-A/final_response.txt), [trace](runs/T09-r1-A/phase1/transcript.jsonl) |
| T09-r1-B | turn_budget | [independent tests](runs/T09-r1-B/tests_after.json), [patch](runs/T09-r1-B/patch.diff), [response](runs/T09-r1-B/final_response.txt), [trace](runs/T09-r1-B/phase1/transcript.jsonl) |
| T10-r1-A | turn_budget | [independent tests](runs/T10-r1-A/tests_after.json), [patch](runs/T10-r1-A/patch.diff), [response](runs/T10-r1-A/final_response.txt), [trace](runs/T10-r1-A/phase1/transcript.jsonl) |
| T10-r1-B | turn_budget | [independent tests](runs/T10-r1-B/tests_after.json), [patch](runs/T10-r1-B/patch.diff), [response](runs/T10-r1-B/final_response.txt), [trace](runs/T10-r1-B/phase1/transcript.jsonl) |

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
      "run_id": "T08-r2-A",
      "error_type": "KeyboardInterrupt",
      "stop_requested_by_user": true,
      "reason": "Operator interrupt or harness/environment error. Partial artifacts retained; no automatic retry."
    }
  }
]
```

Stop/incompletion record: {"run_id": "T08-r2-A", "error_type": "KeyboardInterrupt", "stop_requested_by_user": true, "reason": "Operator interrupt or harness/environment error. Partial artifacts retained; no automatic retry."}

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
