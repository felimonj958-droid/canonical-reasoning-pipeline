# Evaluation Pipeline

This package contains the judge and batch-evaluation path for synthetic LR records. It scores canonical records with an LLM judge, aggregates batch-level metrics, estimates cost, and writes evaluation artifacts for inspection and comparison.

## What this package does

The evaluation flow is designed to answer two questions:

- How well did each record score under the current rubric?
- How does the batch perform across flaw types, dimensions, latency, and cost?

The package supports both single-record judging and batch-level aggregation.

## Main chain

The live evaluation path is:

`evaluate_batch -> _load_records_from_batch_summary -> judge_record -> aggregate_scores -> MLflowTracker`

At the record level, the judging path is:

`build_judge_prompt -> client.generate -> parse JSON -> JudgeScore -> JudgeResult`

## Files

### `judge_rubric.py`
Defines the scoring rubric, rubric dimensions, high-quality threshold, and the prompt used by the judge.

Main responsibilities:
- define score structure,
- map canonical record metadata,
- build the judge prompt,
- identify high-quality records.

Key functions and objects:
- `JudgeScore`
- `HIGH_QUALITY_THRESHOLD`
- `RUBRIC_DIMENSIONS`
- `_resolve_canonical_metadata`
- `build_judge_prompt`

### `llm_judge.py`
Scores one record at a time with the LLM judge.

Main dependencies:
- `src.evaluate.judge_rubric`
- `src.llm_client`

Key functions and objects:
- `JudgeResult`
- `_extract_json_block`
- `judge_record`

Use this when you want to understand single-record scoring behavior, parse failures, runtime failures, or judge output handling.

### `run_evaluation.py`
Batch evaluator that loads records referenced by a batch summary, runs the judge, aggregates results, and writes an evaluation JSON artifact.

Main dependencies:
- `src.evaluate.judge_rubric`
- `src.evaluate.llm_judge`
- `src.llm_client`
- `src.tracking`

Key functions and objects:
- `_estimate_judge_cost`
- `_load_records_from_batch_summary`
- `aggregate_scores`
- `evaluate_batch`

Use this when you want the batch-level evaluation story, token accounting, cost estimates, latency, and per-flaw-type breakdowns.

## Dependency flow

This package depends on the canonical artifacts created by the normalize layer.

Upstream inputs:
- `data/normalized/batches/*.json`
- `data/normalized/records/*.json`

Internal dependencies:
- judge prompt building in `judge_rubric.py`
- LLM access through `src.llm_client`
- experiment tracking through `src.tracking`

Downstream outputs:
- JSON evaluation artifacts in `data/evaluations/`
- optional MLflow run metadata

## What to inspect first

If you are debugging or extending evaluation, inspect these files in order:

1. `judge_rubric.py`
2. `llm_judge.py`
3. `run_evaluation.py`
4. a sample file in `data/evaluations/`

## Commands

Run batch evaluation:

```bash
python -m src.evaluate.run_evaluation <batch_summary_path>
```

Run a smoke evaluation on the first 6 loaded records:

```bash
python -m src.evaluate.run_evaluation <batch_summary_path> 6
```

Inspect recent evaluation outputs:

```bash
python - <<'PY'
from pathlib import Path
p = Path('data/evaluations')
for f in sorted([x for x in p.glob('*.json') if x.is_file()], key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
    print(f)
PY
```

## Notes

- Judge output is expected to be JSON-only, but the parser is tolerant of surrounding fences or prose.
- A record can fail in three ways: `scored`, `parse_error`, or `runtime_error`.
- Batch evaluation is intentionally read-only with respect to the underlying records; it only loads and scores them.
- If the judge model changes, update both the prompt expectations and the cost table together.
