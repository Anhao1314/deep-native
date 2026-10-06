# Pilot Benchmark v1: INCONCLUSIVE

> **Scoring contract defect: raw frozen scores are preserved, but this campaign is invalid for quality comparison.** Task prompt authorizes functionality-related edits, but the manifest allowlist omitted more_itertools/more.pyi. Both agents added legitimate public API type declarations. External contract and upstream regressions passed; FAIL came only from this unintended scope restriction. See [issue record](grading_contract_issue.json).

Planned **60 runs**; completed **8**. Evidence integrity: **PASS**. Exact schedule complete: **False**. Quality comparison valid: **False**. All figures and interpretations below are generated from retained artifacts.

Configuration: Claude Code 2.1.289 (Claude Code); requested model deepseek-flash[1m]; endpoint https://api.deepseek.com/anthropic; Deep Native commit `fda3dd010e7de8f8c1ee1953e006e577464aa3d6`. A and B use the frozen task prompts and budgets; B adds the frozen Skill and hooks.

## Core questions

**Completion rate.** Observed retained scores: A 3/4 (75.0%), B 3/4 (75.0%); B minus A +0.0 percentage points. The campaign is incomplete or has validity issues; these raw scores do not support a final quality conclusion.

**False completion.** Invalid marked completions: A 0/3 (0.0%), B 0/2 (0.0%); the observed claim-conditional rate is unchanged. Unknown declarations: A 1, B 2. These denominators cover marked completion claims, not all responses.

**Long tasks and recovery.** T08 bounded multi-step PASS: A 0/0, B 0/0. Valid T09 staleness observations: A 0/0, B 0/0; stale marked completions in these observations: A 0, B 0. Valid T10 interrupted recoveries: A 0/0, B 0/0; success among valid recoveries: A unavailable, B unavailable. Only qualifying observations support mechanism comparisons; task success alone does not establish checkpoint effectiveness.

**Efficiency tradeoff.** Median agent duration: A 87.9 s, B 101.1 s. Median context-processing tokens: A 281,666.0 (3/4 available), B 589,143.0 (3/4 available). Across common available pairs, median B/A ratios are 1.4 for duration and 1.8 for tokens. Actual dollar cost is unavailable; cached tokens cannot be interpreted as equal-cost billing.

**Task improvements and regressions.** Tasks with more B passes: none. Tasks with fewer B passes: none. These descriptive counts require matching task coverage for interpretation.

## Overall results

| Metric | A: Raw DeepSeek | B: Deep Native |
| --- | ---: | ---: |
| Task Success Rate | 75.0% | 75.0% |
| Verified Completion / declared done | 100.0% | 100.0% |
| Verified Completion / all runs | 75.0% | 50.0% |
| False Completion / declared done | 0.0% | 0.0% |
| PASS count | 3 | 3 |
| Runs | 4 | 4 |
| Declared done | 3 | 2 |
| False completions | 0 | 0 |
| Unknown declaration | 1 | 2 |
| Runs with out-of-scope changes | 1 | 1 |
| Runs with protected-test modifications | 0 | 0 |
| Median agent duration (s) | 87.9 | 101.1 |
| Median including setup and independent grade (s) | 89.0 | 104.9 |
| Median tokens (available runs) | 281,666.0 | 589,143.0 |
| Median tool calls | 19.5 | 31.5 |
| Median changed files | 2.5 | 2.0 |
| Median lines changed | 108.5 | 119.5 |
| Actual API cost | unavailable | unavailable |

Token availability: A 3/4, B 3/4. Incomplete SSE usage is unavailable and is not estimated. Totals include cached input; they measure context processing, not billing.

| Token category | A median / available total | B median / available total |
| --- | ---: | ---: |
| input_tokens | 16,179.0 / 46,266 | 21,804.0 / 60,028 |
| output_tokens | 15,248.0 / 39,386 | 21,803.0 / 59,701 |
| cache_read_input_tokens | 247,808.0 / 820,352 | 545,536.0 / 1,438,976 |
| cache_creation_input_tokens | 0.0 / 0 | 0.0 / 0 |

## Paired comparison

Complete pairs: 4; B wins 0, B losses 0, ties 4. Task-mean B minus A: +0.0 percentage points.
95% task-cluster bootstrap interval: [0.0, 0.0] percentage points, using 4 task clusters, 20,000 samples and seed 91271. This describes uncertainty on this curated task set, not population superiority or equivalence.

| Paired efficiency metric | Available pairs | Median B minus A | Median B / A |
| --- | ---: | ---: | ---: |
| duration_seconds | 4 | 26.6 | 1.4 |
| total_tokens | 3 | 131,092.0 | 1.8 |

## Success by task type

| Type | A PASS / runs | B PASS / runs |
| --- | ---: | ---: |
| cross_file_bug | 0/0 | 0/0 |
| edge_case_validation | 0/0 | 0/0 |
| error_recovery | 0/1 | 0/1 |
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
| T07 | error_recovery | 0/1 | 0/1 |
| T08 | multi_step_long_horizon | 0/0 | 0/0 |
| T09 | verification_staleness | 0/0 | 0/0 |
| T10 | interruption_recovery | 0/0 | 0/0 |

## Trace-derived behavior

These are deterministic command-pattern proxies, not subjective quality scores.

| Behavior | A true / available | B true / available |
| --- | ---: | ---: |
| inspection_before_edit | 4/4 | 4/4 |
| reproduction_before_edit | 3/4 | 4/4 |
| executed_verification | 4/4 | 4/4 |
| successful_verification | 4/4 | 4/4 |
| continued_after_failed_verification | 3/3 | 2/2 |
| edit_after_last_verification | 1/4 | 1/4 |
| risk_reported | 0/4 | 2/4 |
| verification_claim_without_detected_success | 0/4 | 0/4 |

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
| T07 | 1 | FAIL | FAIL |

## Failures

| Run | Classification | Evidence |
| --- | --- | --- |
| T07-r1-A | out_of_scope_changes | [independent tests](runs/T07-r1-A/tests_after.json), [patch](runs/T07-r1-A/patch.diff), [response](runs/T07-r1-A/final_response.txt), [trace](runs/T07-r1-A/phase1/transcript.jsonl) |
| T07-r1-B | out_of_scope_changes | [independent tests](runs/T07-r1-B/tests_after.json), [patch](runs/T07-r1-B/patch.diff), [response](runs/T07-r1-B/final_response.txt), [trace](runs/T07-r1-B/phase1/transcript.jsonl) |

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
    "issue": "retained_scoring_contract_issue",
    "details": {
      "status": "INVALID_FOR_QUALITY_COMPARISON",
      "affected_runs": [
        "T07-r1-A",
        "T07-r1-B"
      ],
      "issue": "Task prompt authorizes functionality-related edits, but the manifest allowlist omitted more_itertools/more.pyi. Both agents added legitimate public API type declarations. External contract and upstream regressions passed; FAIL came only from this unintended scope restriction.",
      "required_next_step": "Correct the allowlists for public API/type-stub maintenance, validate prompt/criteria agreement, freeze a new campaign and rerun. Do not relabel current frozen results after seeing outputs.",
      "raw_scores_preserved": true,
      "model_calls_stopped": true
    }
  },
  {
    "issue": "retained_campaign_stop",
    "details": {
      "reason": "User interrupted the active turn; background runner was explicitly stopped to prevent further API calls. All completed and partial artifacts retained.",
      "completed_runs": 8,
      "started_runs": 9,
      "planned_runs": 60,
      "stop_requested_by_user": true,
      "grading_contract_issue": "grading_contract_issue.json",
      "results_not_suitable_for_quality_comparison": true
    }
  }
]
```

Stop/incompletion record: {"reason": "User interrupted the active turn; background runner was explicitly stopped to prevent further API calls. All completed and partial artifacts retained.", "completed_runs": 8, "started_runs": 9, "planned_runs": 60, "stop_requested_by_user": true, "grading_contract_issue": "grading_contract_issue.json", "results_not_suitable_for_quality_comparison": true}

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
