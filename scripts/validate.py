#!/usr/bin/env python3
"""Schema-based validator for inter-stage data files.

Thin dispatcher to the jsonschema library. schemas/*.schema.json is the source
of truth for shape contracts; there is no per-shape validator code.

CLI usage:
    python -m scripts.validate <schema_name> <data_path>
    python -m scripts.validate grading path/to/grading.json

Programmatic API:
    from scripts.validate import check
    ok, errors = check("grading", Path("grading.json"))

Exit codes (CLI):
    0 — valid
    1 — invalid (structured errors on stderr)
    2 — schema or file missing
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import NamedTuple

try:
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import ValidationError
except ImportError:
    print(
        "error: jsonschema not installed. Run: pip install jsonschema",
        file=sys.stderr,
    )
    sys.exit(2)


SCHEMAS_DIR = Path(__file__).parent.parent / "schemas"


class ShapeError(NamedTuple):
    field: str
    problem: str

    def format(self) -> str:
        return f"  field: {self.field}\n  problem: {self.problem}"


def _schema_path(name: str) -> Path:
    return SCHEMAS_DIR / f"{name}.schema.json"


def check(schema_name: str, data_path: Path) -> tuple[bool, list[ShapeError]]:
    """Programmatic API. Returns (ok, errors).

    Raises FileNotFoundError if the schema or data file is missing — those are
    structural problems, not shape errors, and callers should handle them
    explicitly.
    """
    schema_path = _schema_path(schema_name)
    if not schema_path.exists():
        raise FileNotFoundError(f"schema not found: {schema_path}")
    if not data_path.exists():
        raise FileNotFoundError(f"data file not found: {data_path}")

    schema = json.loads(schema_path.read_text())
    data = json.loads(data_path.read_text())
    validator = Draft202012Validator(schema)
    raw_errors = sorted(
        validator.iter_errors(data), key=lambda e: list(e.absolute_path)
    )

    errors = [
        ShapeError(
            field="/".join(str(p) for p in err.absolute_path) or "<root>",
            problem=err.message,
        )
        for err in raw_errors
    ]
    return (len(errors) == 0, errors)


def _cli(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2

    schema_name, data_path_str = argv[1], argv[2]
    try:
        ok, errors = check(schema_name, Path(data_path_str))
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"error: {data_path_str} is not valid JSON: {exc}", file=sys.stderr)
        return 1

    if ok:
        print(f"ok: {data_path_str} matches schemas/{schema_name}.schema.json")
        return 0

    print(
        f"invalid: {data_path_str} fails schemas/{schema_name}.schema.json",
        file=sys.stderr,
    )
    print(f"{len(errors)} error(s):", file=sys.stderr)
    for err in errors:
        print(err.format(), file=sys.stderr)
    print(
        "\nFix the upstream stage that produced this file. Do not bypass.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(_cli(sys.argv))
