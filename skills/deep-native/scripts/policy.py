#!/usr/bin/env python3
"""Deterministic adaptive policy for the Deep Native v0.2 candidate."""
from __future__ import annotations

import argparse
import json
import sys


class PolicyError(ValueError):
    """Invalid policy input."""


SCOPES = ("local", "cross-file", "repo-wide")
UNCERTAINTY = ("clear", "uncertain")
FAILURE_KINDS = ("implementation", "hypothesis", "contract", "environment", "dependency", "budget", "unknown")


def choose_mode(*, scope: str, uncertainty: str, failures: int = 0,
                interruption_risk: bool = False, long_running: bool = False,
                high_risk: bool = False) -> dict:
    if scope not in SCOPES:
        raise PolicyError(f"scope must be one of: {', '.join(SCOPES)}")
    if uncertainty not in UNCERTAINTY:
        raise PolicyError(f"uncertainty must be one of: {', '.join(UNCERTAINTY)}")
    if type(failures) is not int or failures < 0:
        raise PolicyError("failures must be a non-negative integer")

    deep_reasons = []
    standard_reasons = []
    if high_risk:
        deep_reasons.append("high_risk_change")
    if interruption_risk:
        deep_reasons.append("interruption_risk")
    if long_running:
        deep_reasons.append("long_running_task")
    if failures >= 2:
        deep_reasons.append("two_or_more_ineffective_attempts")
    if scope == "repo-wide":
        deep_reasons.append("repo_wide_scope")

    if scope == "cross-file":
        standard_reasons.append("cross_file_scope")
    if uncertainty == "uncertain":
        standard_reasons.append("uncertain_root_cause")
    if failures == 1:
        standard_reasons.append("first_failed_attempt")

    if deep_reasons:
        mode = "deep"
        reasons = deep_reasons + standard_reasons
        workflow = ["inspect", "reproduce", "classify", "begin", "checkpoint", "verify", "review", "finish"]
    elif standard_reasons:
        mode = "standard"
        reasons = standard_reasons
        workflow = ["inspect", "reproduce", "hypothesis", "edit", "targeted-check", "broader-check", "deliver"]
    else:
        mode = "fast"
        reasons = ["localized_clear_low_risk_task"]
        workflow = ["inspect", "edit", "targeted-check", "deliver"]

    return {
        "schema": 1,
        "mode": mode,
        "runtime_required": mode == "deep",
        "reasons": reasons,
        "workflow": workflow,
        "escalate_when": [
            "a second ineffective attempt occurs",
            "scope expands to repo-wide",
            "interruption or compaction becomes likely",
            "the change becomes high-risk or hard to roll back",
        ],
    }


def failure_action(kind: str, repeated: bool = False) -> dict:
    if kind not in FAILURE_KINDS:
        raise PolicyError(f"kind must be one of: {', '.join(FAILURE_KINDS)}")
    actions = {
        "implementation": "Inspect the failing behavior and diff, then make the smallest code correction before rerunning a focused check.",
        "hypothesis": "Stop editing. Re-read evidence, form an alternative root-cause hypothesis, and test it before another code change.",
        "contract": "Re-read the acceptance condition and existing tests. Do not weaken tests or redefine success to obtain green output.",
        "environment": "Adapt the invocation, writable paths, shell form, or sandbox assumptions before changing product code.",
        "dependency": "Inspect the pinned/runtime dependency state. Repair the environment if authorized; otherwise report the blocker.",
        "budget": "Checkpoint confirmed facts, changed files, current hypothesis, and next action, then stop cleanly instead of rushing completion.",
        "unknown": "Gather one new discriminating observation before retrying. Do not repeat an unchanged failing command.",
    }
    return {
        "schema": 1,
        "kind": kind,
        "repeated": bool(repeated),
        "action": actions[kind],
        "escalate_to_deep": bool(repeated) or kind == "budget",
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    route = sub.add_parser("route", help="Classify a task into fast, standard, or deep mode")
    route.add_argument("--scope", choices=SCOPES, required=True)
    route.add_argument("--uncertainty", choices=UNCERTAINTY, required=True)
    route.add_argument("--failures", type=int, default=0)
    route.add_argument("--interruption-risk", action="store_true")
    route.add_argument("--long-running", action="store_true")
    route.add_argument("--high-risk", action="store_true")
    failure = sub.add_parser("failure", help="Return the next action for a classified failure")
    failure.add_argument("--kind", choices=FAILURE_KINDS, required=True)
    failure.add_argument("--repeated", action="store_true")
    return p


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "route":
            result = choose_mode(scope=args.scope, uncertainty=args.uncertainty,
                                 failures=args.failures, interruption_risk=args.interruption_risk,
                                 long_running=args.long_running, high_risk=args.high_risk)
        else:
            result = failure_action(args.kind, args.repeated)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except PolicyError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
