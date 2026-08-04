# Source Layout

This directory contains the runnable application code for the synthetic-first canonical reasoning pipeline. The current runtime is OpenAI-primary and organized as a small set of pipeline packages with clear handoffs between generation, normalization, validation, persistence, evaluation, and API serving.

## How the code is organized

The active path is intentionally narrow:

`src.generate -> src.normalize -> src.validate -> src.persist`

The evaluation path is parallel to that core flow:

`src.evaluate -> src.llm_client -> src.tracking`

The API surface reuses the same canonical record and persistence code used by the pipeline:

`src.api -> src.normalize / src.validate / src.persist`

## Packages

### `src/api`
FastAPI app and records route for creating canonical records through the service layer.

Main dependencies:
- `src.normalize.canonical_mapper`
- `src.validate.confidence_checks`
- `src.validate.review_routing`
- `src.persist.filesystem_store`

Key entrypoints:
- `src/api/main.py`
- `src/api/routes.py`

### `src/classify`
Document chunking and classification helpers. This package is present but is not part of the main synthetic LR runtime path.

Key functions:
- `choose_strategy`
- `chunk_text`
- `prepare_classification_payload`

### `src/evaluate`
Judge prompt construction, single-record scoring, and batch evaluation/aggregation.

Main dependencies:
- `src.llm_client`
- `src.tracking`
- `src.evaluate.judge_rubric`

Key entrypoints:
- `src/evaluate/llm_judge.py`
- `src/evaluate/run_evaluation.py`
- `src/evaluate/judge_rubric.py`

### `src/generate`
Synthetic LR generation, parsing, validation, and content-quality checks.

Main dependencies:
- `src.llm_client`

Key entrypoints:
- `src/generate/synthetic_lr.py`
- `src/generate/validation.py`
- `src/generate/content_quality_checks.py`

### `src/llm_client`
Backend abstraction for model calls. The current baseline uses OpenAI.

Key entrypoints:
- `src/llm_client/base.py`
- `src/llm_client/openai_client.py`
- `src/llm_client/__init__.py`

### `src/normalize`
Canonical mapping and synthetic LR orchestration. This is the heart of the live pipeline.

Main dependencies:
- `src.generate.synthetic_lr`
- `src.generate.validation`
- `src.generate.content_quality_checks`
- `src.normalize.synthetic_mapper`
- `src.persist.filesystem_store`
- `src.validate.confidence_checks`
- `src.validate.review_routing`
- `src.llm_client`
- `src.tracking`

Key entrypoints:
- `src/normalize/run_synthetic_lr_lane.py`
- `src/normalize/run_synthetic_lr_batch.py`
- `src/normalize/canonical_mapper.py`
- `src/normalize/synthetic_mapper.py`

### `src/persist`
Canonical Pydantic models and filesystem persistence.

Key entrypoints:
- `src/persist/models.py`
- `src/persist/filesystem_store.py`

### `src/tracking`
MLflow tracking wrapper and Git SHA helper.

Main dependencies:
- `mlflow`
- `git` metadata from the local repository

Key entrypoints:
- `src/tracking/mlflow_tracker.py`

### `src/validate`
Canonical validation and review routing.

Key entrypoints:
- `src/validate/confidence_checks.py`
- `src/validate/review_routing.py`

### `src/ingest`
Legacy or placeholder package retained for compatibility. It is not part of the active synthetic LR path.

### `src/ocr`
Legacy or placeholder package retained for compatibility. It is not part of the active synthetic LR path.

## Main runtime chain

The live synthetic LR lane runs in this order:

`generate_synthetic_lr -> clean_synthetic_lr_output -> parse_synthetic_lr_output -> validate_synthetic_lr_payload -> run_content_quality_checks -> map_synthetic_lr_to_record -> validate_record -> choose_destination -> save_record`

The batch runner wraps that lane and adds summary logging:

`run_synthetic_lr_batch -> run_synthetic_lr_lane -> MLflowTracker -> batch summary JSON`

The evaluation path follows saved batch outputs and record files:

`evaluate_batch -> _load_records_from_batch_summary -> judge_record -> aggregate_scores -> MLflowTracker`

## Dependency highlights

A few important file-to-file relationships:

- `src/api/routes.py` uses canonical mapping, validation, review routing, and filesystem persistence.
- `src/normalize/run_synthetic_lr_lane.py` is the most complete live orchestration module.
- `src/normalize/run_synthetic_lr_batch.py` depends on the lane runner and tracking.
- `src/evaluate/run_evaluation.py` depends on the judge and tracking layers.
- `src/evaluate/llm_judge.py` depends on the judge rubric and the LLM client abstraction.
- `src/generate/synthetic_lr.py` is the generation entrypoint feeding the lane.

## Recommended deep-dive READMEs

Keep this umbrella README at the root of `src/`, then add only the most useful deeper docs:

- `src/normalize/README.md` — the main orchestration and canonical mapping path.
- `src/evaluate/README.md` — the judge and evaluation path.
- `src/api/README.md` — if you want a concise service surface overview.

## Useful commands

Show structure:

```bash
find src -maxdepth 3 -print | sort
```

Show file inventory by package:

```bash
find src -type f | awk -F/ '{
  path=""
  for (i=1; i<=NF-1; i++) {
    path = path (i==1 ? $i : "/" $i)
    counts[path]++
  }
}
END {
  for (k in counts) print counts[k], k
}' | sort -nr
```

Find imports:

```bash
grep -R "from src\|import src" -n src tests | sort
```

Find public function definitions:

```bash
python - <<'PY'
from pathlib import Path
import re
for f in sorted(Path('src').rglob('*.py')):
    text = f.read_text()
    defs = re.findall(r'^\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', text, flags=re.M)
    if defs:
        print(f'\n{f}')
        for d in defs:
            print(f'  - {d}')
PY
```

Run the main pipeline:

```bash
python -m src.normalize.run_synthetic_lr_batch
```

Run evaluation:

```bash
python -m src.evaluate.run_evaluation <batch_summary_path>
```

## Notes

This repository is intentionally lean. Not every package in `src/` is equally active, and some folders remain as compatibility stubs or future expansion points. Focus documentation on the live chain first, then only add deeper READMEs where the workflow is complex enough to need them.
