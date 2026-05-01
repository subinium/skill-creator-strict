# Stages

Contract documentation for **per-stage Python scripts in pipeline-type skills produced by skill-creator v2**. The skill-creator itself doesn't have stage scripts — this README is what authors of pipeline skills must follow.

## CLI shape

```
python -m stages.<stage_name> --in <input_path> --out <output_path> \
    --workspace <ws> --iteration <n>
```

## First action — validate input

```python
from scripts.validate import check
ok, errors = check("<schema_name>", input_path)
if not ok:
    for e in errors:
        print(e.format(), file=sys.stderr)
    sys.exit(1)
```

Don't repair the input. Don't warn-and-continue. The runtime LLM reads the structured error and fixes the producer.

## Last action — validate output and update state

```python
from scripts.workflow_state import finish_stage

ok, errors = check("<output_schema>", output_path)
if not ok:
    sys.exit(1)  # stage bug — surface immediately

finish_stage(workspace, name="<this_stage>", iteration=n,
             output_paths=[str(output_path)])
```

If a stage produces invalid output, that's a stage bug — exit non-zero rather than passing corrupted data downstream.

## stages/ vs agents/

The boundary is **reproducibility given identical inputs**:
- Reproducible → `stages/` (Python script)
- Non-deterministic / requires LLM judgment → `agents/` (subagent prompt template)

A stage script that calls an LLM API directly is in the wrong place. Move it to `agents/`.

## Anti-patterns

- Reading files outside the declared `--in` path (makes inputs implicit)
- Skipping validation "for speed" (microseconds saved, hours of debugging spent)
- Catching the validator's exit and continuing (loses the contract)
- Mutating input files (stages must be functional — input → output, no side effects on the input)
