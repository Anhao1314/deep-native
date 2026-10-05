# v0.1.0 validation report

This report describes executed checks, not model capability claims.

## Local environment

Linux, Python 3.13.5, Git 2.47.3. Chromium 144.0.7559.96 was available for rendering.
Claude Code was not on PATH; DeepSeek/Anthropic credentials were absent. External DNS
requests from the authoring container failed. The connected local execution runner was
also unavailable (`tunnel_client_not_seen`); no credentialed host test was substituted.

## Executed results

| Check | Observed result |
| --- | --- |
| `python -m unittest discover -s tests -v` under coverage | **61 tests passed** in 18.774 seconds |
| Runtime CLI statement coverage | **91%**, 419 statements, 39 missed; not branch/model coverage |
| `python examples/demo.py --output docs/demo` | **12/12 expected outcomes** |
| Original retry fixture | **3 tests failed**, as expected |
| Same fixture after explicitly scripted repair | **3 tests passed** |
| Premature `finish` | Exit **2**, rejected |
| `verify` on failing fixture | Exit **1**, failed receipt |
| `finish` after source changed | Exit **2**, stale evidence rejected |
| External fixture grader, seeded bugs | Rejected |
| External fixture grader, scripted reference | Accepted by all 12 contract test methods |
| Equal source/task hashes across raw/skill/claude fixtures | Passed |
| Chromium rendering, 1280×900 and 390×844 | 12 step sections, no horizontal overflow or page errors |
| Python compilation | Passed |

Browser file navigation was blocked by the environment's administrator policy. The
same generated HTML was therefore rendered with Playwright `set_content` in Chromium;
this is a rendering check, not a deployed-site or file-navigation test. Screenshots
were inspected. There are no external page resources or live model widgets.

[Raw unittest output](test-output.txt) · [Machine-readable record](validation.json) ·
[Executed demo transcript](demo/demo.json)

## Negative paths tested

Missing checks, premature completion, nonzero exits, timeouts, missing executables,
source changes, new/deleted files, executable-bit and symlink-target changes, Git HEAD
changes, ignored/tracked file distinctions, changed check contracts, checks mutating
source, latest failure replacing an earlier pass, failed final receipt write, absent
or wrong-task receipts, missing required check evidence, shell metacharacters passed
literally, model credential stripping, redaction, corrupted state, hook parse failures,
matching/other sessions, bounded Stop continuation, blocked vs complete, task adoption,
concurrent mutation lock, nested-project rejection, unsafe managed paths, idempotent
installation, preservation of settings, modified-install refusal, and hook execution
from paths containing spaces.

This is not an exhaustive fault model. Disk failures after a filesystem replacement,
hostile same-user races, external dependency changes and adversarial receipt forgery
are not covered by the assurance claim.

## Explicitly unverified

- Actual Claude Code discovery, variable substitution and complete hook lifecycle.
- Actual DeepSeek requests, authentication, stream/tool-call behavior or token use.
- Native Claude execution and comparative task success, cost or latency.
- macOS/Python 3.10 execution in the authoring container. A CI matrix is provided;
  its remote run status must be inspected separately rather than inferred here.

No percentages of model improvement are claimed. The CI workflow runs only local
helper/fixture tests and the offline demo. Even a green CI run does not fill in any
of the live-model gaps above.

## Reproduce

```bash
python3 -m unittest discover -s tests -v
python3 examples/demo.py --output artifacts/reproduction
```

Coverage is optional and not a project runtime dependency. With the coverage package
installed separately, use `coverage run --source=skills/deep-native/scripts -m unittest
discover -s tests -v`, then `coverage report`. Compare functional outcomes, not elapsed
times or random task IDs. The validation JSON records hashes of the tested source files.
