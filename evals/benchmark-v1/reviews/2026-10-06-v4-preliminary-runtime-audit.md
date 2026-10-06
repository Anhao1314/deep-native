# Preliminary v4 runtime audit

**Artifact/configuration integrity: PASS. Runtime environment: sandbox shell failures observed.**

The 21 retained runs match the frozen schedule prefix. The operator intentionally stopped after run 21 finalized; the next scheduled entry has no artifact directory or API run. This is a stage result from 21/60 planned runs, not a completed effectiveness experiment.

Ordinary heredoc commands failed to create shell temporary files despite the recorded per-run temporary environment. These are sandbox-induced execution failures, distinct from genuine API/assertion/test failures after a rewritten command executes.

| Observed shell denial | A (10 runs) | B (11 runs) |
| --- | ---: | ---: |
| Denied Bash tool results | 7 | 10 |
| Affected runs | 6 | 8 |
| Heredoc temporary-file denials | 6 | 8 |
| Explicit writes to outside-run `/tmp` files | 1 | 1 |
| Native `mktemp` choosing host user-temp directory | 0 | 1 |
| Denials masked by compound tool exit status | 1 | 3 |

There are 17 denied Bash results across 14 runs. Four return `is_error=false` because later compound commands determine the final tool status. The outside-run `/tmp/wc_fix.patch` and `/tmp/err.txt` denials enforce the intended write boundary; heredoc and native `mktemp` failures constrain ordinary local shell workflows.

Each denied operation has later observed replacement/alternative execution or tests. A rewritten probe can then raise a genuine program/test exception; that is execution recovery, not proof that the program passed. Examples include the seeded T06 bug and deliberately failing pre-fix regression tests. T09-A retries its README probe in phase2, consuming a remaining-stage command. No effect size or counterfactual success correction is inferred from these retries.

The sample therefore has verified evidence integrity but an environment limitation that can affect command attempts, budget and behavior. Raw strict grades, durations, assistant-turn counts and failure traces remain unchanged.

## Integrity checks

- 442 per-run artifact files were SHA-256 verified.
- All 8 current and archived protocol files match the freeze; all 4 Skill files match the original fixed commit and installed copies.
- Child environments, actual CLI initialization, model/effort/configuration, hook settings, shared turns, fixture identity and complete artifact manifests match the protocol.
- Prior native cwd receipt and Git xcrun-cache warning recurrences: 0.
- Processes with cwd in completed workspaces at the final snapshot: 0.
- Interrupted/incomplete provider usage is unavailable in three runs; it was retained and not estimated.

## Exact shell evidence and subsequent execution

| Run | Category | Masked status | Exact output | Trace | Subsequent execution |
| --- | --- | --- | --- | --- | --- |
| T01-r1-B | heredoc_tempfile_denial | False | (eval):1: can't create temp file for here document: operation not permitted | [tool result](../results/2026-10-06-pilot-v4/runs/T01-r1-B/phase1/transcript.jsonl#L8244) | 40,001-value sweep executed with zero mismatches. |
| T01-r1-B | heredoc_tempfile_denial | True | (eval):1: can't create temp file for here document: operation not permitted | [tool result](../results/2026-10-06-pilot-v4/runs/T01-r1-B/phase1/transcript.jsonl#L8246) | Pre-fix regression test failed as intended; this is a program/test result, not another shell denial. |
| T02-r1-A | heredoc_tempfile_denial | False | (eval):1: can't create temp file for here document: operation not permitted | [tool result](../results/2026-10-06-pilot-v4/runs/T02-r1-A/phase1/transcript.jsonl#L12344) | Validation and untouched-iterator probe executed. |
| T02-r1-B | heredoc_tempfile_denial | False | (eval):1: can't create temp file for here document: operation not permitted | [tool result](../results/2026-10-06-pilot-v4/runs/T02-r1-B/phase1/transcript.jsonl#L2760) | Original implementation behavior was observed after the probe was rewritten. |
| T03-r1-B | explicit_outside_run_tmp_write_denial | True | (eval):1: operation not permitted: /tmp/wc_fix.patch | [tool result](../results/2026-10-06-pilot-v4/runs/T03-r1-B/phase1/transcript.jsonl#L4936) | Agent used Git stash without the outside /tmp patch file, then the benchmark check passed. |
| T04-r1-A | heredoc_tempfile_denial | False | (eval):1: can't create temp file for here document: operation not permitted | [tool result](../results/2026-10-06-pilot-v4/runs/T04-r1-A/phase1/transcript.jsonl#L21000) | The blocked ad hoc snippet did not execute; 42 regression tests and the visible benchmark ran successfully. |
| T05-r1-B | heredoc_tempfile_denial | False | (eval):1: can't create temp file for here document: operation not permitted | [tool result](../results/2026-10-06-pilot-v4/runs/T05-r1-B/phase1/transcript.jsonl#L5181) | Rewritten probe executed and raised TypeError from dict(bucket); later 16 regression tests passed. |
| T06-r1-A | heredoc_tempfile_denial | False | (eval):1: can't create temp file for here document: operation not permitted | [tool result](../results/2026-10-06-pilot-v4/runs/T06-r1-A/phase1/transcript.jsonl#L3503) | Rewritten probe executed and exposed an assertion about PathAccessError; a later detailed probe ran. |
| T06-r1-B | heredoc_tempfile_denial | False | (eval):1: can't create temp file for here document: operation not permitted | [tool result](../results/2026-10-06-pilot-v4/runs/T06-r1-B/phase1/transcript.jsonl#L569) | Rewritten probe executed and reproduced the seeded outer-root lookup bug. |
| T06-r1-B | native_mktemp_host_temp_denial | True | mktemp: mkdtemp failed on /var/folders/6x/2c3dc9h12332f39bgtg2z25r0000gn/T/tmp.wfATLc3V9M: Operation not permitted | [tool result](../results/2026-10-06-pilot-v4/runs/T06-r1-B/phase1/transcript.jsonl#L5020) | After intermediate scratch/import mistakes, the workspace-scoped pre-fix test ran and failed 8 tests as intended. |
| T07-r1-A | heredoc_tempfile_denial | False | (eval):1: can't create temp file for here document: operation not permitted | [tool result](../results/2026-10-06-pilot-v4/runs/T07-r1-A/phase1/transcript.jsonl#L4825) | README row inspection ran after conversion to python -c. |
| T07-r1-B | heredoc_tempfile_denial | False | (eval):1: can't create temp file for here document: operation not permitted | [tool result](../results/2026-10-06-pilot-v4/runs/T07-r1-B/phase1/transcript.jsonl#L9149) | README formatting probe ran after conversion to python -c. |
| T08-r1-A | explicit_outside_run_tmp_write_denial | True | (eval):1: operation not permitted: /tmp/err.txt | [tool result](../results/2026-10-06-pilot-v4/runs/T08-r1-A/phase1/transcript.jsonl#L19750) | The /tmp stderr file was denied; later 56 regression tests and the visible benchmark passed. |
| T08-r1-A | heredoc_tempfile_denial | False | (eval):1: can't create temp file for here document: operation not permitted | [tool result](../results/2026-10-06-pilot-v4/runs/T08-r1-A/phase1/transcript.jsonl#L19905) | The ad hoc CLI heredoc did not execute; later 56 regression tests and the visible benchmark passed. |
| T08-r1-B | heredoc_tempfile_denial | False | (eval):1: can't create temp file for here document: operation not permitted | [tool result](../results/2026-10-06-pilot-v4/runs/T08-r1-B/phase1/transcript.jsonl#L17164) | Argparse exploration ran after conversion to python -c; final strict grade remained FAIL. |
| T08-r2-B | heredoc_tempfile_denial | False | (eval):1: can't create temp file for here document: operation not permitted | [tool result](../results/2026-10-06-pilot-v4/runs/T08-r2-B/phase1/transcript.jsonl#L22739) | Argparse exploration ran after conversion to python -c. |
| T09-r1-A | heredoc_tempfile_denial | False | (eval):1: can't create temp file for here document: operation not permitted | [tool result](../results/2026-10-06-pilot-v4/runs/T09-r1-A/phase1/transcript.jsonl#L11594) | The README probe was retried in phase2, spending a remaining-stage command; visible benchmark later passed, final updated independent contract still failed. |

## Measurement caveat

T09-r1-A phase1 marks a version-query command (`ruff --version`, `mypy --version`, `pytest --version`) as successful verification. It runs no tests. The raw flag is retained but cannot establish a successful agent check or a qualifying green verification receipt; independent phase1 grading remains PASS.

[Detailed machine-readable audit](2026-10-06-v4-preliminary-runtime-audit.json)

## Scope limits

- No hidden model-weight or backend prompt-cache attestation is possible from these local artifacts.
- Process ownership covers observed descendants; the final process check is a current cwd snapshot.
- Sandbox read guarantees apply to the recorded Documents/temp deployment and declared runtime exceptions.
- Unplanned heredoc/native temp shell denials affect both arms at different observed frequencies; the retained sample cannot isolate a pure Skill effect from the task/command strategy and this environment interaction.
