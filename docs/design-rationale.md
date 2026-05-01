# Design Rationale

Decision history for skill-creator-strict. Each decision is recorded as thesis-antithesis-synthesis so the reasoning can be challenged without redoing the analysis. Decisions occasionally get corrigenda when audit reveals a wrong call — those are kept inline so the reversal is visible.

---

## Decision 1 — Two audiences, two documents

**Thesis:** One `SKILL.md` per skill (upstream's approach).

**Antithesis:** A single `SKILL.md` mixes two distinct addressees: the LLM authoring/iterating the skill, and the LLM consuming it at runtime. Sections like *Capture Intent* speak to the former; *Running and evaluating test cases* to the latter. The mix causes runtime LLMs to drift into meta-discussion of how the skill was built.

**Synthesis:** Split.
- `SKILL.md` — runtime instructions only, loaded by Skill tool dispatch
- `AUTHORING.md` — author-only operational notes
- `docs/design-rationale.md` — this file

The split is the prerequisite for several subsequent decisions.

---

## Decision 2 — Skill type is explicit

**Thesis:** Every skill produced by skill-creator-strict is a pipeline skill with `workflow_state.json` + `stages/` + validators.

**Antithesis:** Most real skills change response style or apply a template — they have no inter-stage data handoff. Forcing pipeline structure adds friction without benefit. Upstream's prose looseness is correct for that class.

**Synthesis:** Two skill types, classified at intake:
- `narrative` — prose `SKILL.md` only. Default for skills with no multi-stage execution.
- `pipeline` — multi-stage with explicit data contracts.

Classification rule: pipeline if downstream stages consume structured output. Otherwise narrative.

---

## Decision 3 — Schema-first, validator is thin

**Thesis:** Hand-write per-shape validators.

**Antithesis:** Hand-written validators have their own schema drift, moving the original problem one level up.

**Synthesis:** `schemas/*.schema.json` (JSON Schema 2020-12) is the single source of truth. `scripts/validate.py` is a thin dispatcher to the `jsonschema` library. Shape is defined in one place; everything else delegates.

---

## Decision 4 — Stage-level durable manifest

**Thesis:** Use TaskList (per-session) and memory (cross-session, free-form).

**Antithesis:** TaskList is session-scoped. Memory is unstructured. Neither captures *which stage of the workflow this run is in*. Upstream's `history.json` tracks iterations but not stage progress within an iteration.

**Synthesis:** `workflow_state.json` at workspace root, schema-validated. Tracks stage status, input/output paths, timestamps, per-iteration. The runtime LLM reads it on every invocation; checking a single file is cheap.

Three-tier separation: `workflow_state.json` (durable stages), TaskList (per-session steps), Memory (user preferences). Each has one job.

---

## Decision 5 — Validator-gated transitions

**Thesis:** Skill author writes validators; runtime LLM checks them.

**Antithesis:** Optional checks get skipped. Upstream's ALL-CAPS warnings ("the grading.json must use fields text/passed/evidence") are admissions that prose enforcement does not work — the warning exists because the bug recurred enough times to motivate it, and the warning didn't stop further recurrence.

**Synthesis:** Each stage script's first action validates its declared inputs against the schema. Failure is a non-zero exit with structured error pointing to the offending field. The runtime LLM reads the error and corrects the upstream output. The mechanism is the enforcement.

---

## Decision 6 — agents/*.md is a prompt template directory, not a registration system

**Thesis (initial):** Compile `agents/*.md` to `.claude/agents/*.md` at the skill root for Claude Code subagent_type dispatch.

**Antithesis (post-audit):** Claude Code reads `.claude/agents/` from the *user's project root* or `~/.claude/`, not from arbitrary skill directories. A skill placing `.claude/agents/<name>.md` inside its own dir does not register that subagent for the user's session. The "compile" step was performing `shutil.copy2` and calling it compilation — a feature with no real effect.

**Synthesis:** `agents/*.md` is a prompt template directory. Dispatchers read the file content and include the body in their prompt. This matches upstream's actual dispatch model. No claim of subagent_type registration is made.

If a user wants `subagent_type` registration, they manually copy or symlink to their `.claude/agents/`. That's a user-side concern, not a skill-creator concern.

---

## Decision 7 — Keep `expectations` as the canonical term (corrigendum)

**Thesis (initial):** Rename `expectations` → `assertions` for vocabulary consistency. Upstream mixes the two terms inconsistently; skill-creator-strict should pick one.

**Antithesis (post-audit):** Upstream's actual schemas use `expectations` everywhere; the mixed usage is in prose, not data files. Renaming the schema field cascades into rewriting `aggregate_benchmark.py`, `generate_review.py` (~470 lines), `viewer.html` (~1300 lines), and `eval_review.html`. Cost: 2000+ lines of fork. Benefit: ~20 tokens saved per skill at runtime.

**Synthesis (corrigendum):** Keep `expectations`. Use it consistently in prose too — the goal is removing prose-schema inconsistency, not picking a more aesthetic word. Reverting the rename preserves viewer/aggregator compatibility unchanged.

A useful pattern: when a renaming feels clean, count the consumers it touches before committing.

---

## Decision 8 — workflow_state.json `stages` is an array

**Thesis (initial):** `stages` keyed by stage name, value is the latest record.

**Antithesis (post-audit):** Iteration 2's `run` stage record overwrites iteration 1's. History is lost. The "stage-level durable manifest" claim — the central design advantage — silently fails for any skill that iterates.

**Synthesis:** `stages` is an array of records. Each has `name`, `iteration`, `status`, `input_paths`, `output_paths`, timestamps, optional `error`. Lookups are by `(name, iteration)`. The schema enforces the array shape so the bug cannot recur.

---

## Decision 10 — Name four authoring principles as the philosophical referee

**Thesis:** skill-creator-strict's stage architecture stands on its own technical merits — schema-first contracts, validator-gated transitions, per-iteration manifest. No articulated philosophy needed.

**Antithesis:** Architecture without articulated values drifts. Future maintainers face decisions the architecture doesn't decide for them — should this stage produce more output? should this validator be stricter? should we add a "convenience" feature for one user? Without a stated value system, defaults shift toward addition (the LLM bias), and the line gradually loosens.

**Synthesis:** Name four authoring principles, woven into SKILL.md and mapped to skill-creator-strict's three orientations:

1. **Think before coding** (purpose / intake) — surface ambiguity, present alternatives, push back on overcomplication
2. **Simplicity first** (process / draft) — minimum that solves the problem, no speculation
3. **Surgical changes** (process / improve) — touch only what's required, don't drive-by improve
4. **Goal-driven execution** (result / run-grade-review) — define success criteria, loop until verified

These echo well-known observations on LLM coding pitfalls (Karpathy's framing being the most cited articulation). Naming them gives future maintainers a referee: "does this change uphold or violate these?" If unclear, prefer the principle over the convenience.

The principles aren't a separate doc — they live as named values inside SKILL.md stages and the AUTHORING.md authoring section.

---

## Decision 9 — Carry over upstream scripts unchanged where possible

**Thesis:** Rewrite all upstream scripts in skill-creator-strict style for consistency.

**Antithesis:** `run_loop.py`, `improve_description.py`, `run_eval.py`, `generate_report.py`, `generate_review.py`, `viewer.html` are working code. Rewriting introduces regression risk on a path that works. The places where skill-creator-strict genuinely improves on upstream are localized — input validation, drift detection, structured state.

**Synthesis:** Carry upstream scripts unchanged. Forks happen only where audit reveals a real defect:
- `validate.py` (new)
- `workflow_state.py` (new)
- `new_skill.py` (new)
- `preflight.py` (new)
- `aggregate_benchmark.py` (forked; adds validator hooks at input + output)
- `package_skill.py` (forked; handles `AUTHORING.md`, excludes `workflow_state.json`)

Everything else is byte-identical to upstream. Upstream patches apply cleanly.

---

## Non-goals

These were considered and rejected. Don't add them without revisiting.

1. **Skill-to-skill composition framework.** Out of harness scope.
2. **Pipeline DAG runner.** The LLM is the orchestrator; `workflow_state.json` is descriptive (manifest), not interpreted (program).
3. **Self-hosting skill-creator-strict in a pipeline format.** High cost, low evidence. skill-creator-strict ships a regression eval set in `evals/evals.json` instead.
4. **Auto-rewriting skills from feedback.** Description optimization works because trigger rate is closed-form. Skill rewriting needs human judgment.
5. **Renaming `expectations` → `assertions`.** See Decision 7.
6. **A separate `constraints.yaml`.** Hard rules go in mechanism. Soft rules in prose. A third location drifts.
7. **Compile step from `agents/` to `.claude/agents/`.** See Decision 6.

---

## Open questions

1. Validator retry policy — auto-retry once with the structured error, or surface immediately?
2. Should `AUTHORING.md` be machine-parseable (declared stable contracts vs experimental sections)?
3. Is hand-writing stage scripts the right level forever, or should there eventually be a higher-level declaration that compiles to scripts?
4. Should `workflow_state.json` ever split across multiple files (one per iteration)? Single is simpler today.

These are deliberately unresolved until a real skill forces the decision.
