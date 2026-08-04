# Normalize Pipeline

This package contains the active synthetic LR orchestration path. It is the most important runtime package in the repository because it connects generation, validation, mapping, routing, persistence, and batch reporting.

## What this package does

`src.normalize` turns synthetic LR outputs into canonical records and writes them to the correct destination. It also provides the batch runner used to produce batch summaries for later evaluation.

The core responsibilities are:

- run one synthetic LR lane,
- run a batch of lane configurations,
- map synthetic payloads into canonical records,
- preserve canonical record shape across the pipeline,
- persist accepted records or review items,
- produce batch summaries for evaluation and MLflow tracking.

## Main chain

The live lane executes in this order:

`generate_synthetic_lr -> clean_synthetic_lr_output -> parse_synthetic_lr_output -> validate_synthetic_lr_payload -> run_content_quality_checks -> map_synthetic_lr_to_record -> validate_record -> choose_destination -> save_record`

The batch runner wraps multiple lane executions and aggregates the results:

`run_synthetic_lr_batch -> run_synthetic_lr_lane -> batch summary JSON -> src.evaluate.run_evaluation`

## Files

### `run_synthetic_lr_lane.py`
Primary lane orchestrator for a single synthetic item or configuration.

Main dependencies:
- `src.generate.synthetic_lr`
- `src.generate.validation`
- `src.generate.content_quality_checks`
- `src.normalize.synthetic_mapper`
- `src.persist.filesystem_store`
- `src.validate.confidence_checks`
- `src.validate.review_routing`
- `src.llm_client`

Key functions:
- `_build_candidate`
- `_build_structural_failure_result`
- `_select_best_candidate`
- `_score_candidate`
- `_candidate_debug_summary`
- `_apply_quality_result_to_record`
- `run_synthetic_lr_lane`

Use this when you want to understand the full per-record control flow.

### `run_synthetic_lr_batch.py`
Batch runner that calls the lane runner across configs, collects metrics, and writes batch summaries.

Main dependencies:
- `src.normalize.run_synthetic_lr_lane`
- `src.llm_client`
- `src.tracking`

Key functions:
- `_estimate_cost_usd`
- `_aggregate_generation_metrics`
- `_write_summary`
- `run_synthetic_lr_batch`
- `main`

Use this when you want batch-level generation, MLflow logging, and summary output.

### `synthetic_mapper.py`
Maps synthetic LR generation output into the canonical record schema.

Main dependencies:
- `src.persist.models`

Key function:
- `map_synthetic_lr_to_record`

### `canonical_mapper.py`
Earlier or more general canonical mapping helper for creating canonical records from source manifests and normalized text.

Main dependencies:
- `src.persist.models`

Key function:
- `map_to_record`

### `clean_text.py`
Text normalization helper used in preprocessing or cleanup flows.

Key function:
- `normalize`

## Dependency flow

This package sits between generation and storage.

Upstream:
- generation lives in `src.generate`
- client access lives in `src.llm_client`

Downstream:
- canonical record models live in `src.persist`
- destination rules live in `src.validate`
- persistence lives in `src.persist.filesystem_store`
- batch summaries are consumed by `src.evaluate`

## What to inspect first

If you are trying to understand the runtime behavior, inspect these files in this order:

1. `run_synthetic_lr_lane.py`
2. `synthetic_mapper.py`
3. `run_synthetic_lr_batch.py`
4. `src.generate.synthetic_lr`
5. `src.validate.confidence_checks`
6. `src.validate.review_routing`
7. `src.persist.filesystem_store`

## Commands

Run the batch pipeline:

```bash
python -m src.normalize.run_synthetic_lr_batch
```

Run a lane-level smoke test or manual call from Python:

```bash
python - <<'PY'
from src.normalize.run_synthetic_lr_lane import run_synthetic_lr_lane
result = run_synthetic_lr_lane()
print(result)
PY
```

Inspect the batch file or latest batch summaries:

```bash
python - <<'PY'
from pathlib import Path
p = Path('data/normalized/batches')
for f in sorted([x for x in p.glob('*.json') if x.is_file()], key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
    print(f)
PY
```

## Notes

- The active lane path is OpenAI-primary.
- This package is the best place to study the actual synthetic LR product behavior.
- If generation or validation changes, this is usually the first package that needs documentation updates.
- If you only maintain one deep-dive source README, keep it here.
