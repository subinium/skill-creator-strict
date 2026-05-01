# skill-creator-strict

Schema-first skill authoring with validator-gated stage transitions. A drop-in alternative to [`anthropics/skills/skill-creator`](https://github.com/anthropics/skills/tree/main/skills/skill-creator) for skills with multi-stage execution.

[한국어 README](./README.ko.md)

## Why

`skill-creator` enforces inter-stage data contracts via prose imperatives. When the prose fails — for example, when a `grading.json` arrives with `name`/`met` fields instead of the required `text`/`passed` — the next stage silently ingests malformed data and the failure surfaces much later, at viewer-render time or during human review.

`skill-creator-strict` moves those contracts to JSON Schema and inserts a validator at every stage boundary. Malformed data is rejected at the source with a structured error pointing to the offending field.

## Install

```bash
git clone https://github.com/<owner>/skill-creator-strict
cd skill-creator-strict
python -m venv .venv
.venv/bin/pip install jsonschema
```

## Quick start

```bash
# Bootstrap a new skill
python -m scripts.new_skill my-skill --type pipeline --path ~/skills

# Validate an inter-stage file
python -m scripts.validate <schema_name> path/to/file.json
# schemas: workflow | evals | grading | benchmark | feedback | trigger_eval

# Validate an entire workspace
python -m scripts.preflight ~/skills/my-skill-workspace

# Aggregate run results into a benchmark
python -m scripts.aggregate_benchmark <iteration_dir> --skill-name my-skill

# Package for distribution
python -m scripts.package_skill ~/skills/my-skill
```

Runtime runbook for the consumer LLM lives in [`SKILL.md`](./SKILL.md).

## How it compares to skill-creator

| | `skill-creator` | `skill-creator-strict` |
|---|---|---|
| Document split | Single `SKILL.md` mixes runtime + authoring | `SKILL.md` (runtime) + `AUTHORING.md` (authoring) |
| Inter-stage contracts | Prose imperatives | JSON Schema (draft 2020-12) |
| Stage transitions | Implicit, LLM-judged | Validator-gated; refuses malformed input |
| Run state | Directory conventions + flat `history.json` | `workflow_state.json` with per-iteration stage records |
| Skill type | Implicit single shape | Explicit `narrative` vs `pipeline` |
| Bootstrap | Manual file creation | `scripts.new_skill` CLI |
| Preflight | None | `scripts.preflight <workspace>` |

## What carries over from skill-creator

The browser-based eval viewer, the description-optimization loop, and the supporting helpers (`run_loop.py`, `improve_description.py`, `run_eval.py`, `generate_report.py`, `utils.py`, `eval-viewer/*`, `assets/*`) are kept byte-identical from upstream. Patches from upstream apply cleanly. Only the components where validator-gating provides a measurable improvement are forked.

## Layout — side by side with skill-creator

### `anthropics/skills/skill-creator`

```
skill-creator/
├── SKILL.md
├── LICENSE.txt
├── agents/
│   ├── analyzer.md
│   ├── comparator.md
│   └── grader.md
├── assets/
│   └── eval_review.html
├── eval-viewer/
│   ├── generate_review.py
│   └── viewer.html
├── references/
│   └── schemas.md                  ← prose describing JSON shapes
└── scripts/
    ├── aggregate_benchmark.py
    ├── generate_report.py
    ├── improve_description.py
    ├── package_skill.py
    ├── quick_validate.py           ← ad-hoc structural check
    ├── run_eval.py
    ├── run_loop.py
    └── utils.py
```

### `skill-creator-strict`

```
skill-creator-strict/
├── SKILL.md
├── AUTHORING.md                         NEW   authoring notes (separated from runtime)
├── README.md / README.ko.md
├── LICENSE
├── agents/
│   ├── analyzer.md / comparator.md / grader.md
├── assets/
│   └── eval_review.html            carryover
├── docs/
│   └── design-rationale.md         NEW   decision history
├── eval-viewer/
│   ├── generate_review.py          carryover
│   └── viewer.html                 carryover
├── evals/
│   └── evals.json                  NEW   regression test corpus
├── schemas/                        NEW   replaces v1 references/schemas.md (prose → JSON Schema)
│   ├── workflow.schema.json
│   ├── evals.schema.json
│   ├── grading.schema.json
│   ├── benchmark.schema.json
│   ├── feedback.schema.json
│   └── trigger_eval.schema.json
├── scripts/
│   ├── validate.py                 NEW   schema-driven validator (replaces quick_validate)
│   ├── workflow_state.py           NEW   manifest API
│   ├── new_skill.py                NEW   bootstrap CLI
│   ├── preflight.py                NEW   workspace-wide validation
│   ├── aggregate_benchmark.py      FORK  + validator hooks at input/output
│   ├── package_skill.py            FORK  + AUTHORING.md, excludes workflow_state.json
│   ├── run_loop.py                 carryover
│   ├── improve_description.py      carryover
│   ├── run_eval.py                 carryover
│   ├── generate_report.py          carryover
│   └── utils.py                    carryover
└── stages/
    └── README.md                   NEW   stage-script contract for pipeline-skill authors
```

**At a glance:**
- 5 new top-level entries (`AUTHORING.md`, `docs/`, `evals/`, `schemas/`, `stages/`)
- 4 new scripts, 2 forked, 5 carried over byte-identical
- `references/schemas.md` (prose) replaced by `schemas/*.schema.json` (validatable contracts)
- `agents/`, `assets/`, `eval-viewer/` unchanged

## Documentation

- [`SKILL.md`](./SKILL.md) — runtime runbook
- [`AUTHORING.md`](./AUTHORING.md) — authoring conventions
- [`docs/design-rationale.md`](./docs/design-rationale.md) — design decisions and trade-offs
- [`stages/README.md`](./stages/README.md) — stage-script contract for pipeline skills

## Compatibility

- Python 3.11+
- `jsonschema >= 4.0`
- Skill consumers: Claude Code, Claude.ai, Cowork (see SKILL.md for environment-specific notes)

## License

[MIT](./LICENSE)

## Authoring principles

The skill also embeds four authoring principles — *think before coding*, *simplicity first*, *surgical changes*, and *goal-driven execution* — woven into the corresponding stages. See [`docs/design-rationale.md`](./docs/design-rationale.md#decision-10) for how each maps.

## Acknowledgements

Built on the design and substantial code of [`anthropics/skills/skill-creator`](https://github.com/anthropics/skills/tree/main/skills/skill-creator).
