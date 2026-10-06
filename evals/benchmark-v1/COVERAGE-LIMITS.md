# Acceptance coverage and trace interpretation

The independent grader checks finite functional contracts, upstream regressions,
submitted regression tests, protected-file hashes and allowed modification scope.
A strict PASS means these checks passed. It does not prove complete code quality,
semantic documentation quality, performance, or every possible input behavior.

| Task | Coverage limit |
| --- | --- |
| T04 | Seeded ranges, selected malformed strings and two delimiter combinations; no exhaustive grammar or performance guarantee. |
| T08 | Core API roundtrips and three CLI examples; malformed compact and usage paths are not exhaustive. Parser reuse and meaningful API/CLI coverage in submitted tests are not semantically enforced. |
| T09 | Signature, defaults, outputs and fill identity are checked. Laziness is checked through the first default-padded chunk; later chunks and unpadded streaming are less constrained. |
| T10 | Grouping, caps, callback counts, identity, exceptions and validation before consumption are checked. The keyword-only `max_run` signature and unusual iterator protocols are not independently asserted. |

Verification freshness compares source bytes observed at tool returns. A matching
fingerprint does not establish that a test covered the newly requested behavior;
custom, asynchronous or redirected checks require trace review. In particular,
T09 review should inspect whether post-change tests exercise `pad=False`.

Recovery evidence requires an actual SIGKILL, corroborating phase-one exit status,
distinct sessions and the shared budget. A checkpoint file at interruption does
not establish that the next session read it or that it caused success. Mutation
interrupts and 90-second fallback interruptions should be distinguished.

Missing completion markers are unknown, not false completion. Unsupported test
language and stale verification are review flags; absent regex matches are never
proof of fabricated execution. Failed infrastructure wrappers must be separated
from the actual command and test output, as the excluded v3 campaign demonstrates.

These limits were recorded before the first formal v4 call. They do not rescore
historical results or change the frozen acceptance criteria.
