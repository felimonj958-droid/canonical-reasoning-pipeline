
## `PROJECT_STATUS.md`

```md
# Project Status
## Test Status

The focused synthetic LR suite is currently green: 17 passed. The core lane, batch, cost-metrics, and review-routing tests now align with the current canonical schema and no longer depend on the retired `LSATInfo` model. [memory:1]

Current active test coverage includes:

- `tests/test_run_synthetic_lr_lane.py`
- `tests/test_run_synthetic_lr_batch.py`
- `tests/test_batch_cost_metrics.py`
- `tests/test_synthetic_lr_review_routing.py`

The test suite is intentionally lean. Duplicate or legacy-specific tests should be removed rather than preserved when they no longer represent a distinct production seam. [memory:1]


## Current state

Milestone: lean OpenAI-primary synthetic LR baseline
# Project Status

## Current state

The repository has been trimmed to better match the active synthetic-first pipeline. Legacy or duplicate test surfaces have been reduced, and the remaining test modules are being aligned with the current canonical-record schema and `/records` API contract. [memory:1]

## Recent cleanup

Completed or in-progress cleanup items:

- Replaced legacy LSAT-specific validation references with current metadata-oriented schema usage where applicable.
- Updated canonical validation terminology from `missing_section` to `missing_content_group`.
- Consolidated API testing around the current `/records` route.
- Identified duplicate API test files for removal where they no longer cover a distinct contract.
- Continued reducing stale ingest-oriented naming in tests and supporting modules. [memory:1]

## Current status

The synthetic LR pipeline is in a clean post-refactor state. The focused suite is green at 17 passed, and the production code no longer depends on the retired `LSATInfo` schema. [memory:1]

### Test posture

The current active test set is lean and focused on live seams:

- lane orchestration.
- batch orchestration.
- generation cost and latency aggregation.
- synthetic low-quality review routing. [memory:1]

### Cleanup completed

- Removed the schema mismatch caused by `LSATInfo`.
- Updated synthetic mapping to the new `RecordMetadata` model.
- Aligned lane tests to the current selection-summary contract.
- Kept batch and review-routing tests aligned to the active synthetic-first pipeline. [memory:1]

### Next work

Continue trimming any duplicate or legacy test files that no longer cover a distinct behavior, and keep documentation synchronized with the current synthetic-first contract. [memory:1]

## Current status

The synthetic-first canonical reasoning pipeline is in a stable post-refactor state. The full test suite is green at 71 passed with 1 skipped, and the active code path now uses the `RecordMetadata` schema. [memory:1]

### Completed cleanup

- Removed the `LSATInfo` dependency from the active mapper path.
- Aligned lane and batch tests to the current selection metadata contract.
- Kept the batch cost aggregation and review-routing tests aligned with the current wrapper behavior.
- Preserved a lean test surface focused on live production seams. [memory:1]

### Active coverage

- `tests/test_api_records.py`
- `tests/test_batch_cost_metrics.py`
- `tests/test_classification_chunking.py`
- `tests/test_content_quality_checks.py`
- `tests/test_evaluation_aggregation.py`
- `tests/test_llm_client.py`
- `tests/test_llm_judge.py`
- `tests/test_mlflow_tracker.py`
- `tests/test_openai_client.py`
- `tests/test_run_synthetic_lr_batch.py`
- `tests/test_run_synthetic_lr_lane.py`
- `tests/test_synthetic_lr.py`
- `tests/test_synthetic_lr_review_routing.py`
- `tests/test_synthetic_lr_validation.py` [memory:1]

### Next work

Keep trimming any remaining duplicate or legacy tests that no longer represent a distinct seam, and keep the docs synchronized with the active synthetic-first contract. [memory:1]


## Active test posture

The suite is being kept lean by mapping each remaining test file to a live production seam:

- `tests/test_api_records.py` — current API contract for canonical record creation.
- `tests/test_run_synthetic_lr_lane.py` — lane-level synthetic generation behavior.
- `tests/test_run_synthetic_lr_batch.py` — batch orchestration and result summaries.
- `tests/test_batch_cost_metrics.py` — batch cost and latency aggregation.
- `tests/test_synthetic_lr_persistence.py` — persistence-specific behavior, if still distinct.
- `tests/test_synthetic_lr_review_routing.py` — review-routing behavior against current validation semantics. [memory:1]

Any test file that only duplicates coverage under older naming should be removed rather than preserved. [memory:2]

## Current focus

Near-term work is focused on:

- finishing schema-consistency cleanup after the metadata refactor,
- resolving remaining collection issues in synthetic LR tests,
- deleting duplicate legacy-named tests,
- keeping docs synchronized with the actual active API and validation contract. [memory:1]

## v1 direction

The v1 target remains a lean, reproducible canonical reasoning pipeline with:

- strict record schemas,
- OpenAI-primary synthetic generation,
- deterministic validation and review routing,
- filesystem persistence for normalized and review queues,
- focused tests tied to real production seams instead of historical structure. [memory:1][memory:2]

Current verified state:

- OpenAI is the active backend for the main workflow.
- Synthetic LR is the primary public pipeline.
- Multi-candidate synthetic LR orchestration is implemented.
- Deterministic payload validation and content-quality checks are active.
- Canonical mapping, review routing, and filesystem persistence are wired end to end.
- Batch generation, evaluation, and MLflow tracking remain active.
- The repository is in a lean cleanup state ahead of freezing `baseline_v1` and `eval_set_v1`.

## Repository status

The active repository now centers on one clear path:

- synthetic LR generation,
- structural parsing and payload validation,
- deterministic quality checks,
- canonical mapping,
- canonical validation,
- review routing,
- filesystem persistence,
- batch generation and summary artifacts,
- evaluation and report generation,
- MLflow-tracked experimentation,
- DVC-aware reproducibility work around canonical artifacts.

This makes the repo easier to read as a portfolio project and reduces drift
between the documented system and the actual runtime surface.

## Validation

Verified in the current cleanup state when:

- targeted synthetic LR lane and batch tests passed,
- synthetic LR canonical and persistence behaviors remained intact after source trimming,
- FastAPI remained part of the active codebase,
- evaluation and persistence paths stayed in place,
- removed legacy lanes did not break the main workflow surface.

## Active commands

From repo root:

```bash
cd ~/Documents/canonical-reasoning-pipeline
pytest -q
python -m src.normalize.run_synthetic_lr_batch
python -m uvicorn src.api.main:app --reload

# Project Status

- OpenAI is the active runtime path. [memory:6]
- Synthetic LR is the primary workflow. [memory:6]
- The full test suite is green at 73 passed and 1 skipped. [conversation_history:1]

## Current state

The synthetic-first pipeline is operational across generation, validation, routing, persistence, and batch orchestration for Logical Reasoning flaw items. [memory:6] A recent small audit batch completed successfully with 3 valid items, 3 normalized destinations, 3 quality passes, no quality flags, and no runtime errors across `causal`, `necessary_vs_sufficient`, and `sampling`. [conversation_history:1]

## Batch audit note

The latest persisted audit batch (`batch_openai_1per_1cand_20260803_145225`) produced one item for each active flaw family and showed clean routing and stable generation metrics. [conversation_history:1] Batch-level metrics for that run were 3,449 prompt tokens, 505 completion tokens, 3,954 total tokens, estimated cost of 0.00082 USD, and average latency of 2871.83 ms. [conversation_history:1]

## Quality assessment

The pipeline appears technically ready to stage because the current suite is green and the latest audit batch completed cleanly without review-routing or runtime failures. [conversation_history:1][memory:6] The item bank is not fully freeze-ready yet, because at least one causal item still reads as a stock correlation-to-causation template and the sampling item is acceptable but better classified as revise-lite than standout keep quality. [memory:8][conversation_history:1]

## Current judgment

Stage the codebase after this status note and batch evidence are committed. [memory:6] Defer any v1 content freeze until another small batch confirms stronger phrasing diversity, especially reducing stock flaw-label feel and improving distinction among distractors. [memory:8]

## Next actions

- Stage the current pipeline state and docs as the stable synthetic-LR baseline. [memory:6]
- Run another small persisted batch to test phrasing diversity rather than just validity. [memory:8]
- Tighten prompt and quality checks so correct answers are less memorizable across items within the same flaw family. [conversation_history:1][memory:8]
- Keep the human-review rubric and synthetic-quality rubric as lightweight gates before any item-bank freeze decision. [memory:8]

# PROJECT_STATUS

## Evaluation refactor
- Canonical metadata now resolves from `metadata` first, with legacy fallbacks preserved.
- `JudgeResult` now carries `flaw_type` and `difficulty` through all outcomes.
- Batch evaluation now records `load_stats`, per-result canonical metadata, and per-flaw-family aggregates.
- Package exports now include the canonical metadata resolver for shared access.

## Tests
- `test_llm_judge.py` updated for canonical metadata propagation.
- `test_evaluation_aggregation.py` updated for flaw-family aggregation and richer `JudgeResult` objects.
- Full test suite passes: 74 passed, 1 skipped.

## Status
- Refactor is complete and verified.
- Next validation step is a real smoke evaluation batch to confirm saved JSON payload shape in practice.
