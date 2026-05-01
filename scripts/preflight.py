#!/usr/bin/env python3
"""Run all known validators against a workspace before a stage transition.

This is the "are we OK to proceed?" check. It walks the workspace and the
adjacent skill directory, runs the appropriate validator for each known file
shape, and reports a single pass/fail with all errors at once.

Usage:
    python -m scripts.preflight <workspace_dir>

Exit codes:
    0 — all known files valid (or none present)
    1 — at least one validation failure (full report on stderr)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scripts.validate import check


# (schema_name, glob_pattern relative to root)
CHECKS: list[tuple[str, str]] = [
    ("workflow", "workflow_state.json"),
    ("evals", "../*/evals/evals.json"),
    ("evals", "evals/evals.json"),
    ("grading", "iteration-*/eval-*/*/run-*/grading.json"),
    ("grading", "iteration-*/eval-*/*/grading.json"),
    ("benchmark", "iteration-*/benchmark.json"),
    ("feedback", "iteration-*/feedback.json"),
    ("feedback", "feedback.json"),
]


def preflight(workspace: Path) -> tuple[int, list[str]]:
    """Returns (failure_count, lines_of_report)."""
    workspace = workspace.resolve()
    report: list[str] = []
    failures = 0
    checked = 0

    for schema_name, pattern in CHECKS:
        for path in workspace.glob(pattern):
            if not path.is_file():
                continue
            checked += 1
            ok, errors = check(schema_name, path)
            if ok:
                report.append(
                    f"  ok      {schema_name:10} {path.relative_to(workspace)}"
                )
            else:
                failures += 1
                report.append(
                    f"  FAIL    {schema_name:10} {path.relative_to(workspace)}"
                )
                for err in errors:
                    report.append(f"            {err.field}: {err.problem}")

    if checked == 0:
        report.append("  (no known shape files found in workspace)")

    return failures, report


def _cli(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="scripts.preflight")
    p.add_argument("workspace")
    args = p.parse_args(argv[1:])

    workspace = Path(args.workspace)
    if not workspace.is_dir():
        print(f"error: {workspace} is not a directory", file=sys.stderr)
        return 2

    failures, report = preflight(workspace)
    stream = sys.stderr if failures else sys.stdout
    print(f"preflight on {workspace.resolve()}", file=stream)
    for line in report:
        print(line, file=stream)

    if failures:
        print(
            f"\n{failures} file(s) failed validation. Fix before proceeding.",
            file=sys.stderr,
        )
        return 1
    print("\nall validations passed.", file=stream)
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv))
