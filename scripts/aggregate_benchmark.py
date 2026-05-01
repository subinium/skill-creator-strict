#!/usr/bin/env python3
"""Aggregate per-run grading.json files into benchmark.json (and benchmark.md).

v2 differences from v1:
- Validates every grading.json against schemas/grading.schema.json before reading
  (catches v1 → v2 field name drift early)
- Validates the produced benchmark.json against schemas/benchmark.schema.json
  before writing
- Reuses v1's directory layout and run/config/timing logic — what worked, works

Usage:
    python -m scripts.aggregate_benchmark <iteration_dir> --skill-name <name>

The iteration_dir contains eval-* directories, each with config dirs (with_skill,
without_skill, etc.), each with run-N/grading.json files.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.validate import check


def _stats(values: list[float]) -> dict[str, float]:
    if not values:
        return {"mean": 0.0, "stddev": 0.0, "min": 0.0, "max": 0.0}
    n = len(values)
    mean = sum(values) / n
    if n > 1:
        variance = sum((x - mean) ** 2 for x in values) / (n - 1)
        stddev = math.sqrt(variance)
    else:
        stddev = 0.0
    return {
        "mean": round(mean, 4),
        "stddev": round(stddev, 4),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
    }


def _load_grading(path: Path) -> dict[str, Any]:
    """Validate and load a grading.json. Refuses to silently accept malformed files."""
    ok, errors = check("grading", path)
    if not ok:
        msg = "\n".join(e.format() for e in errors)
        raise ValueError(f"grading.json is invalid at {path}:\n{msg}")
    return json.loads(path.read_text())


def _load_results(iteration_dir: Path) -> dict[str, list[dict[str, Any]]]:
    """Walk eval-*/config/run-*/grading.json. Returns dict[config -> list of run records]."""
    if not list(iteration_dir.glob("eval-*")):
        raise FileNotFoundError(f"no eval-* directories under {iteration_dir}")

    results: dict[str, list[dict[str, Any]]] = {}

    for eval_dir in sorted(iteration_dir.glob("eval-*")):
        meta_path = eval_dir / "eval_metadata.json"
        if meta_path.exists():
            try:
                eval_id = json.loads(meta_path.read_text()).get("eval_id", 0)
            except json.JSONDecodeError:
                eval_id = 0
        else:
            try:
                eval_id = int(eval_dir.name.split("-", 1)[1])
            except ValueError:
                eval_id = 0

        for config_dir in sorted(p for p in eval_dir.iterdir() if p.is_dir()):
            run_dirs = sorted(config_dir.glob("run-*"))
            if not run_dirs:
                continue
            results.setdefault(config_dir.name, [])
            for run_dir in run_dirs:
                grading_file = run_dir / "grading.json"
                if not grading_file.exists():
                    print(f"warning: no grading.json in {run_dir}", file=sys.stderr)
                    continue
                grading = _load_grading(grading_file)

                summary = grading.get("summary") or _summary_from_expectations(
                    grading["expectations"]
                )
                timing = _timing(grading, run_dir)
                metrics = grading.get("execution_metrics", {})
                notes = _notes(grading)

                run_number = int(run_dir.name.split("-", 1)[1])
                results[config_dir.name].append(
                    {
                        "eval_id": eval_id,
                        "run_number": run_number,
                        "pass_rate": summary.get("pass_rate", 0.0),
                        "passed": summary.get("passed", 0),
                        "failed": summary.get("failed", 0),
                        "total": summary.get("total", 0),
                        "time_seconds": timing.get("total_duration_seconds", 0.0),
                        "tokens": timing.get("total_tokens", 0),
                        "tool_calls": metrics.get("total_tool_calls", 0),
                        "errors": metrics.get("errors_encountered", 0),
                        "expectations": grading["expectations"],
                        "notes": notes,
                    }
                )

    return results


def _summary_from_expectations(expectations: list[dict[str, Any]]) -> dict[str, float]:
    total = len(expectations)
    passed = sum(1 for e in expectations if e.get("passed"))
    failed = total - passed
    return {
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "passed": passed,
        "failed": failed,
        "total": total,
    }


def _timing(grading: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    timing = grading.get("timing") or {}
    if not timing:
        timing_file = run_dir / "timing.json"
        if timing_file.exists():
            try:
                timing = json.loads(timing_file.read_text())
            except json.JSONDecodeError:
                timing = {}
    return timing


def _notes(grading: dict[str, Any]) -> list[str]:
    notes_summary = grading.get("user_notes_summary", {})
    out: list[str] = []
    for k in ("uncertainties", "needs_review", "workarounds"):
        out.extend(notes_summary.get(k, []))
    return out


def _aggregate(results: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    configs = list(results.keys())
    for config, runs in results.items():
        summary[config] = {
            "pass_rate": _stats([r["pass_rate"] for r in runs]),
            "time_seconds": _stats([r["time_seconds"] for r in runs]),
            "tokens": _stats([float(r.get("tokens", 0)) for r in runs]),
        }

    if len(configs) >= 2:
        primary = summary.get(configs[0], {})
        baseline = summary.get(configs[1], {})
        d_pass = primary.get("pass_rate", {}).get("mean", 0) - baseline.get(
            "pass_rate", {}
        ).get("mean", 0)
        d_time = primary.get("time_seconds", {}).get("mean", 0) - baseline.get(
            "time_seconds", {}
        ).get("mean", 0)
        d_tokens = primary.get("tokens", {}).get("mean", 0) - baseline.get(
            "tokens", {}
        ).get("mean", 0)
        summary["delta"] = {
            "pass_rate": f"{d_pass:+.2f}",
            "time_seconds": f"{d_time:+.1f}",
            "tokens": f"{d_tokens:+.0f}",
        }

    return summary


def build_benchmark(
    iteration_dir: Path,
    *,
    skill_name: str,
    skill_path: str = "",
    executor_model: str = "<model>",
) -> dict[str, Any]:
    results = _load_results(iteration_dir)
    summary = _aggregate(results)

    runs: list[dict[str, Any]] = []
    for config, run_list in results.items():
        for r in run_list:
            runs.append(
                {
                    "eval_id": r["eval_id"],
                    "configuration": config,
                    "run_number": r["run_number"],
                    "result": {
                        "pass_rate": r["pass_rate"],
                        "passed": r["passed"],
                        "failed": r["failed"],
                        "total": r["total"],
                        "time_seconds": r["time_seconds"],
                        "tokens": r.get("tokens", 0),
                        "tool_calls": r.get("tool_calls", 0),
                        "errors": r.get("errors", 0),
                    },
                    "expectations": r["expectations"],
                    "notes": r["notes"],
                }
            )

    eval_ids = sorted({r["eval_id"] for run_list in results.values() for r in run_list})
    runs_per_config = max((len(v) for v in results.values()), default=0)

    return {
        "metadata": {
            "skill_name": skill_name,
            "skill_path": skill_path,
            "executor_model": executor_model,
            "analyzer_model": "",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "evals_run": eval_ids,
            "runs_per_configuration": runs_per_config,
        },
        "runs": runs,
        "run_summary": summary,
        "notes": [],
    }


def benchmark_to_markdown(benchmark: dict[str, Any]) -> str:
    meta = benchmark["metadata"]
    summary = benchmark["run_summary"]
    configs = [k for k in summary if k != "delta"]
    lines = [
        f"# Benchmark — {meta['skill_name']}",
        "",
        f"- timestamp: {meta['timestamp']}",
        f"- evals: {', '.join(map(str, meta['evals_run']))}",
        f"- runs per configuration: {meta['runs_per_configuration']}",
        "",
        "## Summary",
        "",
        "| config | pass_rate (mean ± stddev) | time_seconds | tokens |",
        "|---|---|---|---|",
    ]
    for config in configs:
        s = summary[config]
        lines.append(
            f"| {config} | "
            f"{s['pass_rate']['mean']:.2f} ± {s['pass_rate']['stddev']:.2f} | "
            f"{s['time_seconds']['mean']:.1f} | "
            f"{int(s['tokens']['mean'])} |"
        )
    if "delta" in summary:
        d = summary["delta"]
        lines += [
            "",
            f"**Delta** (primary - baseline): pass_rate {d['pass_rate']}, "
            f"time {d['time_seconds']}s, tokens {d['tokens']}",
        ]
    return "\n".join(lines) + "\n"


def write_outputs(iteration_dir: Path, benchmark: dict[str, Any]) -> tuple[Path, Path]:
    json_path = iteration_dir / "benchmark.json"
    md_path = iteration_dir / "benchmark.md"
    json_path.write_text(json.dumps(benchmark, indent=2) + "\n")

    ok, errors = check("benchmark", json_path)
    if not ok:
        msg = "\n".join(e.format() for e in errors)
        raise ValueError(
            f"produced benchmark.json is invalid (this is an aggregator bug):\n{msg}"
        )

    md_path.write_text(benchmark_to_markdown(benchmark))
    return json_path, md_path


def _cli(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="scripts.aggregate_benchmark")
    p.add_argument("iteration_dir")
    p.add_argument("--skill-name", required=True)
    p.add_argument("--skill-path", default="")
    p.add_argument("--executor-model", default="<model>")
    args = p.parse_args(argv[1:])

    iteration_dir = Path(args.iteration_dir).resolve()
    if not iteration_dir.is_dir():
        print(f"error: {iteration_dir} is not a directory", file=sys.stderr)
        return 2

    try:
        benchmark = build_benchmark(
            iteration_dir,
            skill_name=args.skill_name,
            skill_path=args.skill_path,
            executor_model=args.executor_model,
        )
        json_path, md_path = write_outputs(iteration_dir, benchmark)
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv))
