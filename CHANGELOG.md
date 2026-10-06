# Changelog

## v0.2 Candidate — Adaptive Runtime

This candidate is not yet claimed as an efficacy improvement.

### Changed

- Replaced one-size-fits-all workflow with FAST / STANDARD / DEEP escalation.
- Persistent checkpoint/evidence lifecycle is now reserved for DEEP work.
- Added explicit failure classes so environment errors do not automatically trigger code edits.
- Added deterministic `policy.py` mirror with offline tests.
- Added v0.1 pilot findings without merging the heavyweight raw artifact branch.
- Added a 12-run mechanism-ablation protocol before any new large benchmark.

### Evidence driving the change

The stopped v0.1 matched preliminary sample was Raw 8/10 vs Deep Native 7/10,
with 0 B wins, 1 B loss, and 9 ties. Deep Native increased post-failure persistence
but also added tool/processing overhead. See `docs/v0.1-pilot-findings.md`.

## v0.1.0

Initial evidence-first Skill, project-scoped installer, worktree-bound verification,
checkpoint recovery, bounded hooks, offline demo, and fixture grader.
