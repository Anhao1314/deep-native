# Contributing

Use Python 3.10+ on macOS/Linux. There are no third-party runtime dependencies.

```bash
python3 -m unittest discover -s tests -v
python3 examples/demo.py --output artifacts/my-demo
```

Add a failing test for a real defect before the repair. Include failure modes and
security boundaries, not just the successful path. Keep SKILL.md small, load detailed
references only when relevant, and avoid rigid ceremony for read-only tasks.

Changes must preserve user permissions, existing configuration and honest completion
states. Never enable a permission bypass, upload user data, search for credentials,
add hidden telemetry, or install global account settings. Do not include sensitive
logs. Document any network access or dependency added in a future version.

A model-performance claim requires task definitions, effective provider/model/host
versions, a held-out protocol, repeated runs and independent grades. Offline fixture
success is not model success. Do not submit invented percentages or unlabeled simulations.
