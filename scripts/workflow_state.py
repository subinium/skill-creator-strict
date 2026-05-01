#!/usr/bin/env python3
"""Read and update workflow_state.json with automatic schema validation.

The manifest at workspace_path/workflow_state.json tracks per-iteration stage
records. This module is the single point that writes to it — direct file edits
should be avoided so that every write is validated.

Programmatic API:
    from scripts.workflow_state import load, start_stage, finish_stage, fail_stage

    state = load(workspace_path)
    start_stage(workspace_path, name="run", iteration=2)
    finish_stage(workspace_path, name="run", iteration=2,
                 output_paths=["iteration-2/eval-0/with_skill/outputs/"])

CLI usage:
    python -m scripts.workflow_state init <workspace> --skill-name <n> --skill-type <narrative|pipeline>
    python -m scripts.workflow_state show <workspace>
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.validate import check


MANIFEST_FILENAME = "workflow_state.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _manifest_path(workspace_path: Path) -> Path:
    return workspace_path / MANIFEST_FILENAME


def _validate(workspace_path: Path) -> None:
    ok, errors = check("workflow", _manifest_path(workspace_path))
    if not ok:
        msg = "\n".join(e.format() for e in errors)
        raise ValueError(f"workflow_state.json is invalid:\n{msg}")


def _save(workspace_path: Path, state: dict[str, Any]) -> None:
    path = _manifest_path(workspace_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n")
    _validate(workspace_path)


def load(workspace_path: Path) -> dict[str, Any]:
    path = _manifest_path(workspace_path)
    if not path.exists():
        raise FileNotFoundError(f"no workflow_state.json at {workspace_path}")
    _validate(workspace_path)
    return json.loads(path.read_text())


def init(
    workspace_path: Path,
    *,
    skill_name: str,
    skill_type: str,
    skill_path: str | None = None,
) -> dict[str, Any]:
    """Create a fresh manifest with current_stage=intake, iteration=1."""
    state: dict[str, Any] = {
        "skill_name": skill_name,
        "skill_type": skill_type,
        "current_stage": "intake",
        "current_iteration": 1,
        "started_at": _now(),
        "stages": [],
    }
    if skill_path:
        state["skill_path"] = skill_path
    state["workspace_path"] = str(workspace_path.resolve())
    _save(workspace_path, state)
    return state


def _find_stage(
    state: dict[str, Any], name: str, iteration: int
) -> dict[str, Any] | None:
    for record in state["stages"]:
        if record["name"] == name and record["iteration"] == iteration:
            return record
    return None


def start_stage(
    workspace_path: Path,
    *,
    name: str,
    iteration: int,
    input_paths: list[str] | None = None,
) -> None:
    state = load(workspace_path)
    if _find_stage(state, name, iteration) is not None:
        raise ValueError(f"stage {name} iteration {iteration} already started")
    state["stages"].append(
        {
            "name": name,
            "iteration": iteration,
            "status": "running",
            "started_at": _now(),
            "input_paths": input_paths or [],
        }
    )
    state["current_stage"] = name
    state["current_iteration"] = iteration
    _save(workspace_path, state)


def finish_stage(
    workspace_path: Path,
    *,
    name: str,
    iteration: int,
    output_paths: list[str] | None = None,
) -> None:
    state = load(workspace_path)
    record = _find_stage(state, name, iteration)
    if record is None:
        raise ValueError(f"stage {name} iteration {iteration} was not started")
    record["status"] = "completed"
    record["finished_at"] = _now()
    if output_paths is not None:
        record["output_paths"] = output_paths
    _save(workspace_path, state)


def fail_stage(
    workspace_path: Path,
    *,
    name: str,
    iteration: int,
    kind: str,
    message: str,
    field: str | None = None,
) -> None:
    state = load(workspace_path)
    record = _find_stage(state, name, iteration)
    if record is None:
        raise ValueError(f"stage {name} iteration {iteration} was not started")
    record["status"] = "failed"
    record["finished_at"] = _now()
    err: dict[str, Any] = {"kind": kind, "message": message}
    if field:
        err["field"] = field
    record["error"] = err
    _save(workspace_path, state)


def mark_complete(workspace_path: Path) -> None:
    state = load(workspace_path)
    state["current_stage"] = "complete"
    _save(workspace_path, state)


def _cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="scripts.workflow_state")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init")
    p_init.add_argument("workspace")
    p_init.add_argument("--skill-name", required=True)
    p_init.add_argument(
        "--skill-type", choices=["narrative", "pipeline"], required=True
    )
    p_init.add_argument("--skill-path")

    p_show = sub.add_parser("show")
    p_show.add_argument("workspace")

    args = parser.parse_args(argv[1:])
    workspace = Path(args.workspace).resolve()

    if args.cmd == "init":
        init(
            workspace,
            skill_name=args.skill_name,
            skill_type=args.skill_type,
            skill_path=args.skill_path,
        )
        print(f"initialized workflow_state.json at {workspace}")
        return 0

    if args.cmd == "show":
        state = load(workspace)
        print(json.dumps(state, indent=2))
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(_cli(sys.argv))
