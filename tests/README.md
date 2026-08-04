# Tests Overview

This directory is organized by live production seam rather than by implementation detail. Each test module maps to one part of the runtime pipeline, so the test suite also serves as a compact reference for how the codebase is wired together.

## Test philosophy

The test suite is intentionally lean:

- one module per meaningful runtime seam,
- focused coverage instead of duplicate legacy tests,
- heavy use of mocks where external services would otherwise make tests slow or brittle,
- clear separation between generation, normalization, validation, persistence, evaluation, API, and tracking.

## Folder contents

### `conftest.py`
Shared fixtures and pytest configuration used across the suite.

### `fixtures/`
Static sample inputs used by tests, including text artifacts for synthetic LR generation and parsing.

### `test_api_records.py`
API route coverage for canonical record creation and review routing.

Main dependency chain:
- `src.api.main`
- `src.persist.filesystem_store`

Key runtime seam:
- `POST /records` behavior

### `test_batch_cost_metrics.py`
Batch cost and latency aggregation helpers.

Main dependency chain:
- `src.normalize.run_synthetic_lr_batch`

Key functions covered:
- `_estimate_cost_usd`
- `_aggregate_generation_metrics`
- batch metric aggregation behavior

### `test_canonical_mapper.py`
Canonical mapping behavior for record construction.

Main dependency chain:
- `src.normalize.canonical_mapper`

### `test_classification_chunking.py`
Classification chunking and payload preparation helpers.

Main dependency chain:
- `src.classify.chunking`

This area is more auxiliary than the synthetic LR core, but it still documents a distinct preprocessing seam.

### `test_content_quality_checks.py`
Heuristic quality gates for synthetic LR outputs.

Main dependency chain:
- `src.generate.content_quality_checks`

Key functions covered:
- `run_content_quality_checks`
- individual content checks such as templating, meta-language, choice quality, and flaw leakage

### `test_evaluation_aggregation.py`
Aggregation logic for judge results and evaluation cost estimation.

Main dependency chain:
- `src.evaluate.judge_rubric`
- `src.evaluate.llm_judge`
- `src.evaluate.run_evaluation`

Key functions covered:
- `aggregate_scores`
- `_estimate_judge_cost`

### `test_llm_client.py`
Integration point for injecting a fake LLM client into generation.

Main dependency chain:
- `src.generate.synthetic_lr`
- `src.llm_client.base`

### `test_llm_judge.py`
Single-record judge behavior and JSON extraction.

Main dependency chain:
- `src.evaluate.judge_rubric`
- `src.evaluate.llm_judge`

Key functions covered:
- `build_judge_prompt`
- `_extract_json_block`
- `judge_record`

### `test_mlflow_tracker.py`
Tracking wrapper behavior and Git SHA helper.

Main dependency chain:
- `src.tracking.mlflow_tracker`

### `test_openai_client.py`
OpenAI backend client behavior and environment handling.

Main dependency chain:
- `src.llm_client.openai_client`
- `src.llm_client`

### `test_run_synthetic_lr_batch.py`
Batch orchestration, candidate threading, selection metadata, and summary writing.

Main dependency chain:
- `src.normalize.run_synthetic_lr_batch`
- `src.normalize.run_synthetic_lr_lane`
- `src.tracking`

### `test_run_synthetic_lr_lane.py`
Single-lane orchestration and routing outcomes for valid, invalid, low-quality, and sampling records.

Main dependency chain:
- `src.normalize.run_synthetic_lr_lane`
- `src.generate.synthetic_lr`
- `src.generate.validation`
- `src.generate.content_quality_checks`
- `src.normalize.synthetic_mapper`
- `src.persist.filesystem_store`
- `src.validate.confidence_checks`
- `src.validate.review_routing`

### `test_synthetic_lr.py`
Prompt generation and cleaning behavior for synthetic LR content.

Main dependency chain:
- `src.generate.synthetic_lr`

### `test_synthetic_lr_integration.py`
Lightweight integration coverage for end-to-end generation and parsing.

Main dependency chain:
- `src.generate.synthetic_lr`

### `test_synthetic_lr_persistence.py`
Persistence-specific behavior, if retained as a distinct seam.

Main dependency chain:
- `src.persist.filesystem_store`

### `test_synthetic_lr_review_routing.py`
Review-routing behavior for low-quality or invalid synthetic LR records.

Main dependency chain:
- `src.normalize.synthetic_mapper`
- `src.persist.models`
- `src.validate.review_routing`

### `test_synthetic_lr_validation.py`
Structural validation for synthetic LR payloads.

Main dependency chain:
- `src.generate.validation`

## Dependency map

The tests roughly mirror the live pipeline:

`src.generate -> src.normalize -> src.validate -> src.persist`

The evaluation tests cover the parallel scoring path:

`src.evaluate -> src.llm_client -> src.tracking`

The API tests cover the service wrapper over the same canonical flow:

`src.api -> src.normalize / src.validate / src.persist`

## What the tests tell you

This suite is not only for correctness; it also shows where the active seams are:

- generation and parsing are validated separately from canonical mapping,
- canonical mapping is validated separately from review routing,
- batch orchestration is validated separately from per-record lane logic,
- evaluation is validated separately from generation,
- external service calls are isolated through mocks or small fixtures.

## Useful commands

List tests:

```bash
find tests -maxdepth 2 -type f | sort
```

Run the full suite:

```bash
pytest -q
```

Run the synthetic LR core slice:

```bash
pytest -q tests/test_run_synthetic_lr_lane.py tests/test_run_synthetic_lr_batch.py tests/test_batch_cost_metrics.py tests/test_synthetic_lr_review_routing.py
```

Run the generation and evaluation slices:

```bash
pytest -q tests/test_synthetic_lr.py tests/test_synthetic_lr_integration.py tests/test_synthetic_lr_validation.py tests/test_content_quality_checks.py tests/test_llm_judge.py tests/test_evaluation_aggregation.py
```

Run the API and persistence slices:

```bash
pytest -q tests/test_api_records.py tests/test_synthetic_lr_persistence.py
```

Inspect imports:

```bash
grep -R "from src\|import src" -n tests | sort
```

Inspect test names:

```bash
python - <<'PY'
from pathlib import Path
import re
for f in sorted(Path('tests').rglob('*.py')):
    text = f.read_text()
    tests = re.findall(r'^\s*def\s+(test_[a-zA-Z0-9_]+)\s*\(', text, flags=re.M)
    if tests:
        print(f'\n{f}')
        for t in tests:
            print(f'  - {t}')
PY
```

## Notes

- `__pycache__` is ignored and should not be documented as part of the living test surface.
- If a test no longer covers a distinct seam, it should be merged or removed rather than preserved as duplication.
- Keep this README aligned with the active runtime surface so it continues to double as a map of the repository.
