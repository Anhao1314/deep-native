# V4 preliminary trace review

Reviewed all **21 completed runs**, including the unpaired `T08-r2-B` PASS. The matched comparison uses **20 runs / 10 pairs**. This is a post-hoc supplement; frozen scores and preregistered behavioral proxies remain unchanged.

| Observation | All A | All B | Matched A | Matched B |
| --- | ---: | ---: | ---: | ---: |
| Real check attempts | 9/10 | 11/11 | 9/10 | 10/10 |
| Completed successful real checks | 8/10 | 8/11 | 8/10 | 7/10 |
| Work continued after a real failed check | 4/5 | 10/10 | 4/5 | 10/10 |
| Later passing check after real failed check | 4/5 | 6/10 | 4/5 | 6/10 |
| Source changed after latest actual passing check | 0/8 | 2/8 | 0/8 | 2/7 |
| Original successful-verification proxy | 9/10 | 10/11 | 9/10 | 9/10 |
| Original inspection-before-edit proxy | 10/10 | 11/11 | 10/10 | 10/10 |
| Original reproduction-before-edit proxy | 5/10 | 9/11 | 5/10 | 9/10 |

Marked DONE: A 5, B 1; invalid marked completions: A 0, B 0. Unknown declarations: A 5, B 10. Seven nonempty final reports were reviewed; their observed verification claims are supported, including retried custom diagnostics. T03 A's verbal completion report omits the exact required final marker and remains unknown.

Tool calls from trace: A 278, B 395; sum of changed-file counts across runs: A 29, B 26. Explicit risk disclosure appears in one available B final report; A has none. Independent semantic totals for investigation/reproduction are unavailable; the original command-pattern values above are retained as proxies.

## Proxy corrections and background follow-up

The original successful-verification proxy counts A 9/10 and B 10/11; actual completed passing checks are A 8/10 and B 8/11. Aggregate false positives: T07-r1-B, T09-r1-A, T09-r1-B. Each is a version probe, not a passing test.

Individual proxy false positives also include a piped ImportError, a blocked pytest command and initial background returns. Background follow-up confirms T04 B and extra T08 B broader jobs were stopped; T06 A broader socket suite failed under permissions, while its required benchmark suite later passed. Copied native outputs are linked in the JSON and saved under [background/](background/). No unsupported broad-suite pass is inferred.

## Staleness and recovery

T09 automatic qualifier: A **1**, B **0**; trace-validated qualifier: A **0**, B **0**. Both phase-1 successful flags come from `pytest --version`, so the required verified-then-changed sequence was not actually observed. A later implements `pad=False` and executes tests, but three newly authored assertions fail. B never implements the public API. Neither arm declares completion.

T10: both arms have actual phase-1 exit `-9` and distinct fresh sessions within the shared budget. Both use the 90-second fallback before source progress. B retains and reads task state, but its checkpoint note is empty. This establishes interruption/state consultation, not checkpoint benefit.

## Decisive failures and scope

- T08-r1-B: shared parser loses duplicate entries via `sorted(set(...))`; required new regressions are absent. Upstream tests pass, but the strict contract fails.
- T09-r1-A: final external contract and upstream tests pass; three erroneous new test assertions fail.
- T09-r1-B and both T10-r1 arms: requested public APIs are absent; T10 required regression tests are also absent.
- All21 strict grades, allowed paths, patch hashes, protected-file hashes and trace tool counts reconcile. Installed treatment files match frozen hashes where locally retained. No score was changed.

## Practical limits

- This is21/60, with only10 complete pairs and one unpaired B success. It cannot answer final efficacy.
- Finite functional contracts do not prove every documented behavior, meaningful regression coverage, parser reuse or general code quality.
- T07 both arms defer predicate evaluation until resumption after yield; full-consumption acceptance does not establish timing under partial consumption.
- Sandbox-induced heredoc, scratch-path and broader socket-suite failures affected optional tool attempts; scope and runtime facts are retained, not repaired retrospectively.
- Actual workflow semantics and cause of overhead require judgment beyond command counts.
- All current T09 phase1 successful proxy flags are version-only, so actual staleness effectiveness is unavailable. T10 fallback interrupts occur before code progress and cannot establish checkpoint benefit.

Detailed per-command UIDs, trace line references, original flags, actual classifications and manual reviews: [trace-review-v4.json](trace-review-v4.json). The frozen artifacts are under [results/2026-10-06-pilot-v4](../results/2026-10-06-pilot-v4/).
