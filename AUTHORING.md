# AUTHORING — conventions for skill authors and maintainers

For people authoring or maintaining this skill. Runtime LLMs stop at SKILL.md.

For the *why* behind each shape (decision history with full reasoning), see `docs/design-rationale.md`. This file is operational.

---

## Authoring philosophy — purpose / process / result

The skill-creator-strict's stage architecture instantiates four principles, mapped to the orientations a skill takes (purpose / process / result):

| Orientation | Stage | Principle |
|---|---|---|
| **Purpose** — *why this skill* | Intake | **Think before coding.** Surface ambiguity, present alternatives, push back when a simpler shape fits. Don't silently pick an interpretation. |
| **Process** — *how it's built* | Draft | **Simplicity first.** The minimum skill that satisfies the intake. The narrative-vs-pipeline split exists to prevent forcing pipeline ceremony on skills that don't need it. |
| **Process** — *how it's revised* | Improve | **Surgical changes.** Fix what feedback identified, nothing else. Drive-by refactoring is out of scope. Every revised line should trace to a specific feedback entry. |
| **Result** — *how it's verified* | Run / Grade / Review | **Goal-driven execution.** Evals are the success criteria; validators verify shape; the human review loop verifies quality. Iterate until criteria are met, not until the prose feels right. |

These principles are woven into SKILL.md at each stage, not bolted on. A change to SKILL.md that violates one of these (e.g., adding speculative features, ALL-CAPS imperatives where a validator would do) is a regression even if functionally correct.

---

## When to add a new stage

A new stage is justified when all three hold:
1. It produces a structured artifact that another stage consumes
2. There's a meaningful failure mode at the boundary
3. It doesn't require new orchestration primitives in the harness

If only #1 or #2 hold, it's a step within an existing stage, not a new stage.

## Mechanism vs prose

| Goes in mechanism (validator/script/schema) | Goes in prose |
|---|---|
| Field names | "How to think about X" |
| Required directory paths | Communication style with the user |
| Stage ordering | Soft heuristics |
| Anything where divergence breaks the next stage | Pedagogical *why* |

If you reach for ALL-CAPS in SKILL.md, that's the signal: move the rule to a validator.

## Adding or changing a schema

New schema if a new stage introduces a new file shape. Extend an existing schema if the same conceptual artifact gains a field.

When extending: update the producer first, then the consumer, then SKILL.md prose. Never the reverse — prose changes that aren't backed by schema/script changes drift silently.

## Shipping an update

1. If conceptual: update `docs/design-rationale.md` first
2. Update the affected schemas
3. Update producer/consumer scripts
4. Update SKILL.md prose
5. Run the regression eval set in `evals/evals.json` against the previously published version
6. Triage regressions; ship improvements

## Naming conventions

- `expectations` — verifiable claims about an output, in `evals.json` and `grading.json`. Matches upstream vocabulary; do not reintroduce `assertions` (see Decision 7).
- `narrative` / `pipeline` — skill type values, lowercase
- `current_stage` values — snake_case, matching script filenames in `stages/`
- Schema filenames — `<entity>.schema.json`. The validator dispatcher uses the prefix.

## Migrating from skill-creator (v1)

- Single `SKILL.md` typically mixes authoring + runtime — split into `SKILL.md` / `AUTHORING.md` on the next iteration
- `grading.json` may use `name`/`met`/`details` from older v1 versions — `scripts.validate grading <path>` reports the drift; fix the producing stage, don't weaken the schema
- Workspace conventions (`iteration-N/eval-X/...`) are preserved; `workflow_state.json` is additive
- `quick_validate.py` is replaced by `scripts.validate` (schema-driven)
- `history.json` is replaced by `workflow_state.json` (richer, per-iteration)

## Non-goals

- Skill-to-skill composition framework (out of harness scope)
- DAG runner (the LLM is the orchestrator; `workflow_state.json` is descriptive)
- Self-hosting in a pipeline format (high cost, low evidence — see `docs/design-rationale.md`)
- Auto-rewriting skills from feedback (needs human judgment)
- A separate `constraints.yaml` (rules go in mechanism or prose, not a third place)
- Renaming `expectations` (preserves viewer/aggregator compatibility — see Decision 7)
- Compiling `agents/` to `.claude/agents/` (Claude Code reads from project root, not skill dir)
