# Security and trust model

Deep Native is a local workflow assistant, not a security boundary or sandbox.
Only use trusted repositories and check commands, or run them in an independently
configured container/VM without secrets, sensitive mounts or unnecessary network access.

The helper has no network client. It does not request API keys, print their values,
change global provider settings, or forward model credentials to checks by default.
Doctor reports presence only. Check output is discarded. Known credential-like strings
and secret environment values are rejected in task/command text. This detection is
best effort, not a complete data-loss-prevention system. Avoid secrets in input entirely.

Check programs and submitted benchmark patches are arbitrary executable code. They can
read files or make network requests. A malicious patch can tamper with tests or exit
a grader early. The evaluation fixture is diagnostic, not an adversarial judge.

Agents with write access can modify the helper, contract, state or receipts. SHA-256
fingerprints detect stale bytes, not malicious forgery. A passing check that does not
exercise the acceptance condition is not proof of correctness. Use independent CI,
review and trusted acceptance tests for higher assurance.

Managed symlink paths are rejected. This is a defense against accidental path escapes,
not a race-free defense against a hostile process on the same filesystem. State writes
are atomic-file replacements, not multi-file transactions. Inspect filesystem errors;
never treat a failed write or an unavailable hook as success.

Report non-sensitive reproduction steps through a GitHub issue. Do not include live
keys, private source or exploitable production details in public issues. Use GitHub's
private vulnerability reporting when enabled; otherwise ask the maintainer for a private
channel without posting the sensitive payload.
