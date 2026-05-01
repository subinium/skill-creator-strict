# Changelog

## v0.1.0 — 2026-05-02

Initial public release.

### Added

- Schema-first inter-stage contracts via JSON Schema (draft 2020-12). Six schemas: `workflow`, `evals`, `grading`, `benchmark`, `feedback`, `trigger_eval`.
- `scripts/validate.py` — thin dispatcher to `jsonschema`. Single source of truth is the schema files.
- `scripts/workflow_state.py` — durable per-iteration manifest with auto-validation on every write.
- `scripts/new_skill.py` — bootstrap CLI for `narrative` or `pipeline` skills.
- `scripts/preflight.py` — workspace-wide validation in one command.
- `scripts/aggregate_benchmark.py` — fork of upstream with validator hooks at input and output.
- `scripts/package_skill.py` — fork of upstream that includes `AUTHORING.md` and excludes `workflow_state.json`.
- Two-document split: `SKILL.md` (runtime) + `AUTHORING.md` (authoring/maintenance).
- `docs/design-rationale.md` — decision history with thesis-antithesis-synthesis structure, including post-audit corrigenda.
- `agents/{grader,comparator,analyzer}.md` — adapted from upstream with validator final-action steps.
- Four authoring principles (think before coding / simplicity first / surgical changes / goal-driven execution) woven into stage descriptions.
- Regression test corpus in `evals/evals.json` (3 cases covering narrative, pipeline, and v1→v2 drift).

### Carried over from `anthropics/skills/skill-creator` (byte-identical)

- `scripts/run_loop.py`, `scripts/improve_description.py`, `scripts/run_eval.py`, `scripts/generate_report.py`, `scripts/utils.py`
- `eval-viewer/generate_review.py`, `eval-viewer/viewer.html`
- `assets/eval_review.html`

### Notes

- Pre-1.0. Field-tested with smoke tests; not yet exercised on long iteration loops.
- Naming: project name pinned to `skill-creator-strict`. The renaming pattern follows TypeScript's `--strict` mode parallel.
