#!/usr/bin/env python3
"""Bootstrap a new skill directory in the v2 layout.

Creates the directory, stub files for the chosen skill type, and an initial
workflow_state.json with current_stage="draft" (intake is treated as completed
because the type decision IS the intake output).

Usage:
    python -m scripts.new_skill <skill-name> --type narrative|pipeline --path <parent-dir>

The skill is created at <parent-dir>/<skill-name>/. Workspace lives next to
the skill at <parent-dir>/<skill-name>-workspace/ — kept separate so eval runs
don't clutter the published skill.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.workflow_state import init as init_state
from scripts.workflow_state import finish_stage, start_stage


KEBAB = re.compile(r"^[a-z][a-z0-9-]*$")


SKILL_MD_TEMPLATE = """---
name: {name}
description: TODO — when to trigger AND what it does (30-80 words, slightly pushy).
---

# {name}

TODO — runtime instructions for the consumer LLM.

Anti-patterns to avoid: ALL-CAPS imperatives (use a validator instead);
mixing authoring intent (goes in AUTHORING.md); restating the description.
"""

AUTHORING_MD_TEMPLATE = """# AUTHORING — {name} conventions

For people authoring or maintaining this skill. Runtime LLM stops at SKILL.md.

## Why this skill exists

TODO

## Naming conventions

- Use `expectations` (not `assertions` or `checks`)
- Stage names: snake_case, matching script filenames in stages/
"""


PIPELINE_DIRS = ["schemas", "stages", "agents", "scripts", "evals"]
NARRATIVE_DIRS = ["evals"]


def _create_layout(skill_dir: Path, skill_type: str) -> None:
    dirs = PIPELINE_DIRS if skill_type == "pipeline" else NARRATIVE_DIRS
    for d in dirs:
        (skill_dir / d).mkdir(parents=True, exist_ok=True)


def _create_files(skill_dir: Path, name: str) -> None:
    (skill_dir / "SKILL.md").write_text(SKILL_MD_TEMPLATE.format(name=name))
    (skill_dir / "AUTHORING.md").write_text(AUTHORING_MD_TEMPLATE.format(name=name))


def bootstrap(name: str, parent: Path, skill_type: str) -> Path:
    if not KEBAB.match(name):
        raise ValueError(f"skill name must be kebab-case, got: {name!r}")

    skill_dir = parent / name
    workspace_dir = parent / f"{name}-workspace"

    if skill_dir.exists():
        raise FileExistsError(f"{skill_dir} already exists")

    skill_dir.mkdir(parents=True)
    workspace_dir.mkdir(parents=True, exist_ok=True)

    _create_layout(skill_dir, skill_type)
    _create_files(skill_dir, name)

    init_state(
        workspace_dir,
        skill_name=name,
        skill_type=skill_type,
        skill_path=str(skill_dir.resolve()),
    )
    start_stage(workspace_dir, name="intake", iteration=1)
    finish_stage(
        workspace_dir,
        name="intake",
        iteration=1,
        output_paths=[str((workspace_dir / "workflow_state.json").resolve())],
    )

    return skill_dir


def _cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="scripts.new_skill")
    parser.add_argument("name")
    parser.add_argument("--type", choices=["narrative", "pipeline"], required=True)
    parser.add_argument("--path", default=".")
    args = parser.parse_args(argv[1:])

    parent = Path(args.path).resolve()
    if not parent.is_dir():
        print(f"error: {parent} is not a directory", file=sys.stderr)
        return 2

    try:
        skill_dir = bootstrap(args.name, parent, args.type)
    except (ValueError, FileExistsError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"created skill at {skill_dir}")
    print(f"workspace at  {parent / f'{args.name}-workspace'}")
    print(
        "intake stage marked completed — next: edit SKILL.md and AUTHORING.md, then start_stage('draft', 1)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv))
