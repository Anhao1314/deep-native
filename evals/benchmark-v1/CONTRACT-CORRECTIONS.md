# Benchmark v1 contract corrections

The stopped `2026-10-06-pilot-v2` campaign keeps its original scores and frozen
protocol. Its two T07 failures were caused solely by an omitted allowed file:
both candidates added legitimate `more_itertools/more.pyi` declarations, while
the independent functional and upstream regression checks passed. Those results
are excluded from the next quality comparison; they are not relabelled.

Before a new campaign is frozen:

- All more-itertools tasks allow the related implementation, type stub, and
  package export files: `more.py`, `more.pyi`, `__init__.py`, and `__init__.pyi`.
  Every task prompt states its exact source file list. A and B still receive
  identical user prompt bytes and the original requested functionality.
- T05, T08, and T10 explicitly require new regression protection. New tests run
  with pytest so both pytest functions and unittest cases are executable; the
  independent grader requires passing, nonempty collection on these tasks.
- T05 requires one loop consuming the input rather than an arbitrary total of
  two `for` statements. An equivalent reduction comprehension is accepted.
- T09's second-stage contract checks that `pad` is keyword-only with default
  `True`, in addition to checking padded and unpadded results.
- T10's invalid-cap tests use an iterable with a consumption counter, so reading
  input before raising the required validation error is rejected.

The offline references supply actual regression tests for the required tasks and
remain grader-validation inputs only. No reference repair is provided to an
agent. Deep Native remains fixed at
`fda3dd010e7de8f8c1ee1953e006e577464aa3d6`.

These corrections do not claim exhaustive proof of documentation quality,
general code quality, or every possible forbidden implementation strategy.
Functional success is grounded in the frozen external contracts, regression
tests, and protected-file and modification-scope checks; traces and patches stay
available for review.

## V3 infrastructure exclusion

`2026-10-06-pilot-v3` was stopped by the operator with SIGINT after **8 completed
runs and 1 partial run** (`T09-r1-B`). This was a technical intervention, not a user
stop request. The frozen sandbox denied writes to Claude Code's native Bash cwd
handoff files, `/tmp/claude-RANDOM-cwd`. Tool results consequently reported wrapper
exit 1 even when successful inner command output was present.

The [infrastructure record](results/2026-10-06-pilot-v3/infrastructure_issue.json)
counts distinct `(phase transcript, tool_use_id)` result events. It excludes
duplicate top-level output copies and assistant narration from the count.

| Run | Completed | Cwd denial results | Marked error / outer exit 1 | Passing-test output in denied result |
| --- | --- | ---: | ---: | ---: |
| T01-r1-A | Yes | 10 | 7 | 2 |
| T01-r1-B | Yes | 22 | 22 | 4 |
| T04-r1-A | Yes | 10 | 9 | 2 |
| T04-r1-B | Yes | 13 | 12 | 5 |
| T06-r1-A | Yes | 13 | 13 | 4 |
| T06-r1-B | Yes | 16 | 16 | 3 |
| T07-r1-A | Yes | 14 | 13 | 3 |
| T07-r1-B | Yes | 17 | 16 | 1 |
| T09-r1-B | No | 6 | 6 | 0 |
| Total | 8 completed + 1 partial | 121 | 114 | 24 |

Two T04-r1-B results explicitly printed inner `EXIT 0` together with outer exit 1
and the denied cwd handoff. One [recorded result](results/2026-10-06-pilot-v3/runs/T04-r1-B/phase1/transcript.jsonl#L23174)
contains passing test counts and empty inner stderr, followed by the wrapper's
denied write. Passing-output counts above are observations, not substituted grades.
Other denied commands may also have genuine inner errors; they are not assumed
successful merely because the wrapper denial is present.

All eight frozen strict outcomes and their raw artifact hashes remain unchanged.
The whole campaign is excluded from quality comparison. Its
[stop record](results/2026-10-06-pilot-v3/campaign_stop.json) forces INCONCLUSIVE,
and its [report](results/2026-10-06-pilot-v3/REPORT.md) is regenerated with the
archived `frozen-harness/analysis.py`. An artifact-integrity PASS covers retained
evidence consistency, not a valid runtime or a completed experiment.

The wrapper issue cannot support a fabrication inference. It also invalidates
treatment attribution from verification-success proxies and time/turn overhead:
agents spent work responding to an infrastructure error. No historical scores or
behavior fields are rewritten to remove that effect.

Before `2026-10-06-pilot-v4` starts, the native Bash handoff behavior must be
restored within an audited boundary. Real Claude CLI smoke checks must demonstrate
correct inner/wrapper success and failure statuses, native shell operation and
cleanup, while tests continue to deny sibling answers and outside-run writes.
The repaired harness must then be frozen anew and all 60 runs restarted. Task
intent and the fixed Deep Native commit remain unchanged; v3 data is not pooled
with the replacement. The repair is an experiment-infrastructure change, not
benchmark-specific Skill tuning.
