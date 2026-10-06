# Preliminary v4 analysis: STOP

Planned 60 runs; retained **21** completed runs. Formal frozen judgment: **INCONCLUSIVE**. This operational recommendation is separate from the preregistered final judgment.

Stop expanding this campaign now: the matched prefix shows no B quality win and at least one B loss. Preserve the user-requested pause and continue offline trace analysis. This is not a population claim that the Skill is ineffective and does not authorize additional API calls.

Read-only evidence integrity: **PASS**; exact frozen prefix: **True**. Raw scores were unchanged.

![Observed retained and matched success rates](<preliminary-v4.svg>)


## Runtime environment limitations

Artifact/configuration integrity is separate from shell compatibility. The expanded audit observed denied native heredoc/temp operations and masked compound-command errors. These can consume turns or alter verification behavior; passing hashes do not make this an anomaly-free measurement of Skill effects.

Across all retained runs there were **17 denied Bash results**: **14 heredoc temp failures**, **3 outside-run/native temp-write denials**, and **4 masked compound results**. A had 7 denials across 6/10 runs; B had 10 across 8/11.

Observed counts from the independent runtime audit:
```json
{
  "A": {
    "runs_reviewed": 10,
    "affected_runs": 6,
    "affected_run_ids": [
      "T02-r1-A",
      "T04-r1-A",
      "T06-r1-A",
      "T07-r1-A",
      "T08-r1-A",
      "T09-r1-A"
    ],
    "denied_bash_tool_results": 7,
    "categories": {
      "heredoc_tempfile_denial": 6,
      "explicit_outside_run_tmp_write_denial": 1
    },
    "masked_compound_tool_results": 1
  },
  "B": {
    "runs_reviewed": 11,
    "affected_runs": 8,
    "affected_run_ids": [
      "T01-r1-B",
      "T02-r1-B",
      "T03-r1-B",
      "T05-r1-B",
      "T06-r1-B",
      "T07-r1-B",
      "T08-r1-B",
      "T08-r2-B"
    ],
    "denied_bash_tool_results": 10,
    "categories": {
      "heredoc_tempfile_denial": 8,
      "explicit_outside_run_tmp_write_denial": 1,
      "native_mktemp_host_temp_denial": 1
    },
    "masked_compound_tool_results": 3
  }
}
```

Later alternative/retry/check evidence is retained, with genuine program/test failures kept separate. Raw strict scores remain unchanged. Isolate these shell quirks offline before any newly authorized model calls.

## All outcomes and matched comparison

| Cohort | A PASS / runs | B PASS / runs |
| --- | ---: | ---: |
| All 21 retained | 8/10 (80.0%) | 8/11 (72.7%) |
| Matched subset | 8/10 (80.0%) | 7/10 (70.0%) |

Unpaired retained runs: T08-r2-B.

Matched pairs: 10; B wins 0, B losses 1, ties 9. Task-mean B minus A: -10.0 percentage points.
Descriptive task-cluster bootstrap range: [-30.0, 0.0] percentage points (10 tasks; 20,000 resamples, seed 91271). No formal statistical conclusion follows from this adaptively stopped snapshot.

## Completion and efficiency

| Metric, all retained runs | A | B |
| --- | ---: | ---: |
| Declared DONE | 5 | 1 |
| Declared BLOCKED | 0 | 0 |
| Unknown declaration | 5 | 10 |
| False completions | 0 | 0 |
| Median agent seconds | 108.0 | 103.7 |
| Median including setup/grading seconds | 115.6 | 110.9 |
| Median tool calls | 29.0 | 36 |
| Median files changed | 2.5 | 2 |
| Median lines changed | 179.5 | 140 |
| Median available tokens | 465,399 | 482,782 |
| Verified Completion / declared DONE | 100.0% | 100.0% |
| Token availability | 9/10 | 9/11 |
| Actual API dollars | unavailable | unavailable |

| Common-pair efficiency | Available pairs | Median B minus A | Median B / A |
| --- | ---: | ---: | ---: |
| agent_seconds | 10 | 15.3 | 1.20x |
| context_processing_tokens | 8 | 107,645.5 | 1.21x |

Tokens include cached context processing; unavailable interrupted usage is not estimated. These are not equal-cost billing tokens.

## Task breakdown

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

## Failure evidence

| Run | Failed strict checks | Declaration | Evidence |
| --- | --- | --- | --- |
| T08-r1-B | contract, new_regression_tests | None | [grade](<../results/2026-10-06-pilot-v4/runs/T08-r1-B/tests_after.json>), [response](<../results/2026-10-06-pilot-v4/runs/T08-r1-B/final_response.txt>), [trace](<../results/2026-10-06-pilot-v4/runs/T08-r1-B/phase1/transcript.jsonl>) |
| T09-r1-A | new_regression_tests | None | [grade](<../results/2026-10-06-pilot-v4/runs/T09-r1-A/tests_after.json>), [response](<../results/2026-10-06-pilot-v4/runs/T09-r1-A/final_response.txt>), [trace](<../results/2026-10-06-pilot-v4/runs/T09-r1-A/phase1/transcript.jsonl>) |
| T09-r1-B | contract | None | [grade](<../results/2026-10-06-pilot-v4/runs/T09-r1-B/tests_after.json>), [response](<../results/2026-10-06-pilot-v4/runs/T09-r1-B/final_response.txt>), [trace](<../results/2026-10-06-pilot-v4/runs/T09-r1-B/phase1/transcript.jsonl>) |
| T10-r1-A | contract, new_regression_tests | None | [grade](<../results/2026-10-06-pilot-v4/runs/T10-r1-A/tests_after.json>), [response](<../results/2026-10-06-pilot-v4/runs/T10-r1-A/final_response.txt>), [trace](<../results/2026-10-06-pilot-v4/runs/T10-r1-A/phase1/transcript.jsonl>) |
| T10-r1-B | contract, new_regression_tests | None | [grade](<../results/2026-10-06-pilot-v4/runs/T10-r1-B/tests_after.json>), [response](<../results/2026-10-06-pilot-v4/runs/T10-r1-B/final_response.txt>), [trace](<../results/2026-10-06-pilot-v4/runs/T10-r1-B/phase1/transcript.jsonl>) |

## Verification and recovery interpretation

The frozen proxy can treat version/help probes as successful verification. Retain its raw counts and use separate actual-execution trace review. Missing regex matches and wrapper errors are not fabrication evidence.

T09 qualification requires independent phase-1 PASS, actual successful functional checking there, and actual later source change. T10 needs actual interruption and distinct sessions; state presence or final PASS alone does not demonstrate checkpoint benefit.

Supplemental trace review: [JSON](<trace-review-v4.json>).

Supplemental runtime audit: [JSON](<2026-10-06-v4-preliminary-runtime-audit.json>).


## Supplemental actual-execution review

| Review measure | All A | All B | Matched A | Matched B |
| --- | ---: | ---: | ---: | ---: |
| Actual functional check attempted | 9/10 | 11/11 | 9/10 | 10/10 |
| Actual completed successful check | 8/10 | 8/11 | 8/10 | 7/10 |
| Frozen successful-verification proxy | 9/10 | 10/11 | 9/10 | 9/10 |

T09 raw qualifying observations were A 1, B 0; actual trace-validated observations were A 0, B 0. Version probes do not establish functional checking. This stage therefore supplies no qualifying verified-then-changed case for either arm.

T10 actual interruption/new-session observations: A 1, B 1. Both used the 90-second fallback before source progress; checkpoint notes were A 0, B 0. B consulted retained state, which does not demonstrate checkpoint benefit.

Final claim review found 0 contradictions in 7 available final reports. This does not attest missing final reports or every intermediate assertion. Raw completion fields and scores remain unchanged.

## Interpretation limits

- The user-requested stop is not the preregistered endpoint; uncertainty is descriptive, not a sequentially valid statistical decision.
- All retained runs are reported; only complete pairs enter matched comparisons and the extra arm is disclosed.
- Ten curated tasks and few repeats cannot establish population superiority, equivalence or broad recovery benefits.
- Raw verification proxies include version/help probes; separate actual-execution review is needed. Original fields remain unchanged.
- Unknown completion declarations limit claim-conditional false-completion interpretation.
- Incomplete SSE usage is unavailable; cached context-processing tokens are not dollar billing.
- Independent strict grades and marker-based Verified Completion are never relabelled by this supplement.
- Configuration and artifact integrity PASS does not imply anomaly-free ordinary shell execution; native heredoc/temp failures limit clean Skill-effect interpretation.
- The bootstrap only resamples observed outcomes; an upper zero with no observed B wins does not exclude benefits on unobserved tasks or repeats.

## Provenance

Claude Code 2.1.289 (Claude Code); model deepseek-flash[1m]; endpoint https://api.deepseek.com/anthropic; Deep Native commit fda3dd010e7de8f8c1ee1953e006e577464aa3d6.

This preliminary stage does not replace the planned design or claim a completed 60-run experiment.
