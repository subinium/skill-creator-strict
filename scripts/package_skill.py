#!/usr/bin/env python3
"""Package a skill folder into a distributable .skill archive.

Differences from upstream skill-creator:
- Validates SKILL.md frontmatter via the schema-driven check (not a separate quick_validate)
- Includes AUTHORING.md (v2 split) in the archive
- Excludes the workspace sibling, .venv, .git, build artifacts
- Pipeline skills: validates schemas/ and ensures workflow_state.json is excluded (it's per-run state, not part of the published skill)

Usage:
    python -m scripts.package_skill <skill_path> [--out-dir <dir>]
"""

from __future__ import annotations

import argparse
import fnmatch
import sys
import zipfile
from pathlib import Path

from scripts.utils import parse_skill_md


EXCLUDE_DIRS = {"__pycache__", "node_modules", ".venv", ".git", ".pytest_cache"}
EXCLUDE_GLOBS = {"*.pyc", "*.pyo"}
EXCLUDE_FILES = {".DS_Store", "workflow_state.json"}
ROOT_EXCLUDE_DIRS = {"evals"}


def _should_exclude(rel_path: Path) -> bool:
    parts = rel_path.parts
    if any(p in EXCLUDE_DIRS for p in parts):
        return True
    if len(parts) > 1 and parts[1] in ROOT_EXCLUDE_DIRS:
        return True
    if rel_path.name in EXCLUDE_FILES:
        return True
    return any(fnmatch.fnmatch(rel_path.name, g) for g in EXCLUDE_GLOBS)


def validate_skill(skill_path: Path) -> tuple[bool, str]:
    """Quick structural check: SKILL.md exists, has parseable frontmatter, has name + description."""
    if not (skill_path / "SKILL.md").exists():
        return False, "SKILL.md not found"
    try:
        name, description, _ = parse_skill_md(skill_path)
    except ValueError as exc:
        return False, f"SKILL.md frontmatter: {exc}"
    if not name:
        return False, "SKILL.md has no name in frontmatter"
    if not description:
        return False, "SKILL.md has no description in frontmatter"
    return True, f"name={name!r}, description present ({len(description)} chars)"


def package(skill_path: Path, out_dir: Path) -> Path:
    skill_path = skill_path.resolve()
    if not skill_path.is_dir():
        raise NotADirectoryError(f"{skill_path} is not a directory")

    ok, msg = validate_skill(skill_path)
    if not ok:
        raise ValueError(f"validation failed: {msg}")

    out_dir.mkdir(parents=True, exist_ok=True)
    skill_filename = out_dir / f"{skill_path.name}.skill"

    added = skipped = 0
    with zipfile.ZipFile(skill_filename, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in skill_path.rglob("*"):
            if not file_path.is_file():
                continue
            arcname = file_path.relative_to(skill_path.parent)
            if _should_exclude(arcname):
                skipped += 1
                continue
            zf.write(file_path, arcname)
            added += 1

    print(f"packaged: {skill_filename}")
    print(f"  validation: {msg}")
    print(f"  files: {added} added, {skipped} skipped")
    return skill_filename


def _cli(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="scripts.package_skill")
    p.add_argument("skill_path")
    p.add_argument("--out-dir", default=".")
    args = p.parse_args(argv[1:])

    try:
        package(Path(args.skill_path), Path(args.out_dir))
    except (ValueError, NotADirectoryError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv))
