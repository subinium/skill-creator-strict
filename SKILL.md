---
name: skill-creator-strict
description: Create new skills, update existing ones, run evals, and optimize triggering. Use whenever the user wants to author a skill, iterate on a skill from feedback, run a benchmark on a skill, or improve a skill's description for triggering accuracy. Pipeline-shaped output with enforced inter-stage contracts.
---

# Skill Creator Strict

Runtime runbook. The workflow is **goal-driven** — evals are the success criteria, validators verify shape at each transition, and the human review loop verifies quality. Iterate until the criteria are met, not until the prose feels right.

Authoring intent and design rationale live in `AUTHORING.md` and `docs/design-rationale.md` — don't read those at runtime.

## First action

Check the current working directory for `workflow_state.json`. If it exists and `current_stage != "complete"`, ask the user: **"Found in-progress workflow at stage `<X>`. Resume, or start fresh?"** Resume by reading the manifest and validating its inputs:

```bash
python -m scripts.preflight <workspace>
```

If validation fails, surface the error first.

## Stage 1 — Intake

Capture intent in at most 2 clarifying questions. Surface ambiguity rather than silently picking — if multiple plausible interpretations exist, present them. If a simpler shape fits (e.g., narrative when pipeline isn't actually needed), say so before classifying. Then bootstrap:

```bash
python -m scripts.new_skill <skill-name> --type narrative|pipeline --path <parent-dir>
```

This creates the directory layout, stub `SKILL.md` + `AUTHORING.md`, and an initial `workflow_state.json` with intake completed.

**Skill type classifier** — set `--type pipeline` only if any of these are true:
- The skill's output is consumed by another automated step
- There's a natural eval loop with objectively verifiable success criteria
- The skill orchestrates multiple subagents or scripts

Otherwise `narrative`. When unsure, default to `narrative` — pipeline-ifying later is cheap; un-pipelining is not.

## Stage 2 — Draft

Write the minimum skill that satisfies the intake. No features beyond what was captured. No "flexibility" or configurability that wasn't requested. Pipeline ceremony (`schemas/`, `stages/`, `agents/`) belongs to pipeline skills only — narrative skills don't pre-emptively add it.

Two documents:
- `SKILL.md` — runtime instructions, imperative voice, addressed to the consumer LLM
- `AUTHORING.md` — design intent and "why this shape," addressed to future authors

**Frontmatter:**

```yaml
---
name: <kebab-case>
description: <when to trigger AND what it does, 30-80 words, slightly pushy>
---
```

The description is the primary triggering mechanism. Cover both *what* and *when-to-use*.

**Anti-patterns in SKILL.md prose:**
- ALL-CAPS imperatives (`MUST`, `NEVER`, `ALWAYS`). If you reach for these, the rule belongs in a validator. Validators give unambiguous structured errors; prose imperatives don't.
- Mixing authoring intent with runtime instructions (that's AUTHORING.md).
- Restating the description.

Explain *why* a step matters. Models adapt to edge cases when given reasoning; over-rigid structures break on prompts the author didn't anticipate.

**Pipeline-only additions:**
- `schemas/*.schema.json` — JSON Schema (draft 2020-12) for every inter-stage data file
- `stages/<name>.py` — one script per pipeline stage, validating input as the first action and output as the last
- `agents/<name>.md` — one per non-deterministic LLM-in-the-loop role. Frontmatter: `name`, `description`, `tools`, `model`. Body is the role prompt. Dispatchers read this file and include the body in their prompt — there is no separate registration step.

## Stage 3 — Test design

Write 2–3 realistic test prompts to `evals/evals.json` (validated by `schemas/evals.schema.json`). Concrete, specific, with backstory — what a real user would type.

Don't write expectations yet. Those come in Stage 4 once you've seen what good outputs look like.

For pipeline skills, also commit to: workspace path convention, which stages are scripts vs agents.

## Stage 4 — Run

```bash
python -m scripts.validate evals evals/evals.json
```

Fix errors before proceeding.

Spawn all test runs in **the same turn** — both with-skill and baseline. Same prompt, no skill (new skill) or previous version (improvement).

```
Agent({
  subagent_type: "general-purpose",
  description: "Run skill on test case <id>",
  prompt: """
Execute this task:
- Skill path: <absolute path to skill>
- Task: <eval prompt>
- Input files: <list or "none">
- Save outputs to: <workspace>/iteration-<N>/eval-<id>/with_skill/run-1/outputs/
Return: one-line status and the list of files produced.
  """
})
```

While runs are in flight, draft expectations and append them to `evals/evals.json`. When subagent tasks complete, the harness notification carries `total_tokens` and `duration_ms` — write each immediately to `<run-dir>/timing.json` (the notification is the only source).

## Stage 5 — Grade and aggregate (pipeline only)

Spawn the grader for each run by reading `agents/grader.md` and using its body as the dispatch prompt. The grader writes `grading.json` per run.

```bash
python -m scripts.aggregate_benchmark <workspace>/iteration-<N> --skill-name <name>
```

The aggregator validates every `grading.json` it reads (refuses malformed inputs) and validates the produced `benchmark.json` (catches aggregator bugs). Outputs: `benchmark.json` and `benchmark.md`.

## Stage 6 — Review

```bash
nohup python <skill-path>/eval-viewer/generate_review.py \
  <workspace>/iteration-<N> --skill-name "<name>" \
  --benchmark <workspace>/iteration-<N>/benchmark.json \
  > /dev/null 2>&1 &
```

For iteration 2+, add `--previous-workspace <prev>`. Headless: `--static <path>`.

Tell the user: "Two tabs — Outputs (per-test feedback) and Benchmark (quantitative). Come back when done."

## Stage 7 — Improve

Read `feedback.json` (validated against `schemas/feedback.schema.json`).

**How to think about improvements:**
1. *Surgical changes.* Fix what the feedback named, nothing else. Drive-by edits to adjacent prose, formatting, or "while I'm here" cleanups are out of scope. Every revised line should trace to a specific feedback entry.
2. *Generalize.* The skill runs on prompts you never see. Fixes that only help these 3 test cases are wrong.
3. *Keep it lean.* Read transcripts, not just outputs. If the skill made the model waste time, that section is pulling negative weight.
4. *Explain the why.* Tempted to write `MUST`? Move the rule to a validator instead.
5. *Bundle repeated work.* If all 3 subagents wrote a similar helper, put it in `scripts/`.

After improving, increment iteration, return to Stage 4. Stop when: user satisfied / feedback empty / no meaningful progress.

## Stage 8 — Optimize trigger

```bash
python -m scripts.validate trigger_eval <trigger-eval.json>
python -m scripts.run_loop \
  --eval-set <trigger-eval.json> --skill-path <skill-path> \
  --model <current-model-id> --max-iterations 5 --verbose
```

Generate the trigger eval set first: 20 queries, mix of should-trigger and should-not-trigger. Realistic phrasings with backstory; the should-not-trigger ones must be near-misses, not obviously irrelevant.

Apply `best_description` to SKILL.md frontmatter.

## Stage 9 — Package

```bash
python -m scripts.package_skill <skill-path>
```

Verify the `.skill` archive contains: `SKILL.md`, `AUTHORING.md`, `evals/`. For pipeline: also `schemas/`, `agents/`, `stages/`, `scripts/`. The packager excludes `workflow_state.json` (it's per-run state, not part of the published skill).

## Advanced — Blind comparison

For "is the new version actually better?" questions where qualitative judgment matters, use `agents/comparator.md` (blind A/B) followed by `agents/analyzer.md` (post-hoc unblinding with concrete suggestions). Optional — most iterations don't need it; the human review loop is usually enough.

## Environment-specific notes

- **Claude.ai** (no subagents): run test cases inline, one at a time. Skip baseline. Show outputs in-conversation instead of viewer. Skip Stage 8 (needs `claude -p`).
- **Cowork** (headless, has subagents): use `--static <path>` for the viewer. Generate the viewer **before** reviewing outputs yourself — get the human in the loop ASAP.

## On validator failures

When any validator rejects a file, **fix the upstream stage that produced it**. Never bypass the validator. Never weaken the schema. The validator's structured error names the offending field — use it.
