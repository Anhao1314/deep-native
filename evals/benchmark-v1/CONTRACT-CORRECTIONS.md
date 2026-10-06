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
