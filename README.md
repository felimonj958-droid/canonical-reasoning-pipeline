
## `README.md`

```md
# canonical-reasoning-pipeline

A synthetic-first canonical reasoning pipeline for generating, validating, routing, and persisting structured reasoning records. The active workflow is OpenAI-primary and centered on stable canonical record contracts rather than legacy OCR-ingest assumptions. [memory:1]

## Overview

This repository focuses on a lean, reproducible workflow for canonical reasoning records:

1. Generate or receive reasoning content.
2. Map payloads into a canonical record.
3. Validate structural and content requirements.
4. Route each record to normalized storage or the review queue.
5. Persist records and batch metadata for inspection and downstream evaluation. [memory:1]

## Core modules

- `src/persist/models.py` — canonical schema definitions.
- `src/api/` — FastAPI routes for record creation and persistence.
- `src/validate/` — validation checks and review-routing logic.
- `src/normalize/` — synthetic generation and batch workflows.
- `src/persist/filesystem_store.py` — normalized and review-queue persistence. [memory:1]

## API contract

The primary API surface is the canonical records route:

- `POST /records` creates a canonical record from the current request contract.
- Records are validated and then routed to normalized storage or the review queue based on validation outcomes. [memory:1]

## Current terminology

The codebase now favors neutral canonical-record terminology:

- `metadata` instead of legacy LSAT-specific structural naming where the schema has been generalized.
- `content_group` instead of legacy `section` terminology in validation and routing.
- `/records` as the active API route instead of older ingest-oriented naming. [memory:1]

## Tests

The test suite is being kept intentionally lean:

- one test module per live production seam,
- no duplicate API test files for the same `/records` behavior,
- current canonical-record naming instead of legacy ingest terminology,
- synthetic lane, batch, routing, and persistence tests aligned to the active schema. [memory:1][memory:2]

Examples of active coverage:

- API record creation and review routing,
- synthetic lane behavior,
- batch summaries and cost metrics,
- persistence behavior for normalized and review outputs. [memory:1]

## Repository direction

This repository is being trimmed for a stable v1: strict schemas, OpenAI-primary synthetic generation, deterministic validation and review routing, and minimal duplicate surface area in tests and docs. [memory:1][memory:2]

## Current stage

The repository is in a lean **OpenAI-primary synthetic LR stage**:

- synthetic LR generation is the main public workflow,
- the canonical record pipeline is wired end to end,
- multi-candidate lane selection is implemented,
- batch generation, evaluation, and MLflow tracking are working,
- DVC is in use for canonical-record reproducibility work,
- legacy OCR/text-ingest and deprecated Ollama-era runtime paths are no longer part of the active repo surface.

## Demo

A short recording of the API in action is available here:  
[Google Drive demo](https://drive.google.com/file/d/1MfuNHaA8uXMr-jhmPBFKPFNiiFlxKaXp/view?usp=sharing).

The demo shows:

- authenticated API access,
- live POST request handling,
- persistence into the canonical pipeline,
- review-path routing for incomplete or invalid records.

## Quickstart

From repo root:

```bash
pytest -q
python -m src.normalize.run_synthetic_lr_batch
python -m uvicorn src.api.main:app --reload
```

Recommended reading order:

1. `PROJECT_STATUS.md` for the current milestone state.
2. `src/normalize/run_synthetic_lr_batch.py` for the main synthetic LR batch entrypoint.
3. `src/normalize/run_synthetic_lr_lane.py` for lane-level orchestration.
4. `src/evaluate/run_evaluation.py` for batch evaluation and reporting.
5. `data/reports/` for current evaluation summaries and retained historical context.

## Active repository scope

The active repository focuses on:

- synthetic LR generation,
- payload validation and content-quality checks,
- canonical mapping and filesystem persistence,
- deterministic review routing,
- batch generation and summary artifacts,
- LLM-as-judge evaluation and report generation,
- MLflow-tracked experimentation,
- DVC-backed reproducibility work for canonical artifacts,
- FastAPI endpoints for the active service surface.

The repository is intentionally lean. Older prototype paths for OCR, document
ingestion, and deprecated local-model workflows are no longer part of the main
runtime or active test surface.

## API token setup

The FastAPI endpoints are protected with a static Bearer token read from the
`API_TOKEN` environment variable.

1. Copy the example environment file:

   ```bash
   cp .env.example .env
   ```

2. Set a local token in `.env`:

   ```env
   API_TOKEN=change-me-local-dev-token
   ```

3. Load the variables into your shell before running the API or tests:

   ```bash
   set -a
   source .env
   set +a
   ```

4. Start the API:

   ```bash
   uvicorn src.api.main:app --reload
   ```

## Docker

### Build locally

```bash
docker build -t canonical-reasoning-pipeline:local .
```

### Run locally

```bash
docker run --rm -p 8000:8000 --env-file .env canonical-reasoning-pipeline:local
```

## Primary lane

The synthetic LR lane is the current first-class workflow:

`generate_synthetic_lr -> clean_synthetic_lr_output -> parse_synthetic_lr_output -> validate_synthetic_lr_payload -> run_content_quality_checks -> map_synthetic_lr_to_record -> validate_record -> choose_destination -> save_record`

Implemented capabilities include:

- prompt-driven LR generation with controlled flaw type and difficulty,
- structural parsing and payload validation,
- deterministic content-quality heuristics,
- multi-candidate generation with best-candidate selection,
- canonical mapping into a stable Pydantic schema,
- review routing for low-quality or structurally invalid outputs,
- persistence of accepted records under `data/normalized/records/`,
- review-queue persistence under `data/review_queue/`,
- batch generation through `src/normalize/run_synthetic_lr_batch.py`,
- evaluation through LLM-as-judge scoring and JSON/Markdown reporting.

## Generation backend

Synthetic generation runs through a provider-agnostic `LLMClient` layer under
`src/llm_client/`. The active backend in this repo stage is:

- `openai` — the primary backend for the current baseline, demo workflow, batch generation, and evaluation path.

Environment variables:

| Variable | Applies to | Purpose |
|---|---|---|
| `LLM_BACKEND` | all | Select backend. Default: `openai`. |
| `OPENAI_API_KEY` | openai | Required. |
| `OPENAI_MODEL` | openai | Default generation model. |
| `OPENAI_BASE_URL` | openai | Optional OpenAI-compatible endpoint. |
| `JUDGE_MODEL` | evaluation | Optional model override for judge scoring. |

## Experiment tracking

Synthetic-generation batches are tracked in MLflow. Runs are stored locally
under `mlruns/` and are not committed to Git. Batch tracking includes parent
batch runs, nested per-config runs, generation-metric aggregation, and summary
artifacts for later comparison. [file:15]

Evaluation runs are also tracked through MLflow, including aggregate score
statistics, judge token usage, cost estimates, and persisted evaluation
artifacts. [file:21]

## Data versioning

Canonical record artifacts are managed with DVC-backed reproducibility work
where appropriate, while evaluation outputs and reports remain in-repo for now
as retained context and prior art.

Current evaluation JSON and report artifacts are being kept temporarily. After a
fresh `baseline_v1` and `eval_set_v1` are generated, frozen, and documented,
older historical artifacts can be reduced for a cleaner long-term repo surface.

## Architecture

The active codebase is organized by pipeline stage under `src/`:

- `src/api/` — FastAPI app and routes,
- `src/evaluate/` — judge rubric, judge execution, and evaluation runs,
- `src/generate/` — synthetic LR generation, parsing, validation, and quality checks,
- `src/llm_client/` — backend abstraction and OpenAI client integration,
- `src/normalize/` — canonical mapping and synthetic lane/batch orchestration,
- `src/persist/` — canonical Pydantic models and filesystem storage,
- `src/tracking/` — MLflow tracking helpers,
- `src/validate/` — canonical validation and review routing.

Key data folders:

- `data/normalized/records/` — accepted canonical records,
- `data/review_queue/` — records routed for review,
- `data/normalized/batches/` — persisted batch summaries,
- `data/evaluations/` — evaluation JSON outputs,
- `data/reports/` — human-readable evaluation summaries.

## Tests

Current local suite status should be treated as a moving repo-state metric, not
a permanent milestone claim. The active repository includes targeted coverage
for:

- synthetic LR generation and parsing,
- lane-level candidate selection and routing,
- batch generation and cost aggregation,
- canonical mapping and persistence,
- validation and review routing,
- evaluation and reporting behavior,
- API-facing active workflows.

## Roadmap

Near-term:

- freeze `baseline_v1`,
- freeze `eval_set_v1`,
- run a fresh evaluation against the frozen pair,
- reduce stale historical evaluation artifacts after the new baseline is documented.

Medium-term:

- expand LR flaw families and difficulty tiers,
- strengthen comparison reporting and evaluation analysis,
- tighten the public service surface around the synthetic LR workflow.

Longer-term:

- add external calibration or comparison lanes without changing the synthetic-first identity,
- explore broader reasoning-task extensions only after the LR baseline is fully frozen and documented.

## Notice and scope

This project is not affiliated with, endorsed by, or sponsored by LSAC, and it
does not redistribute official LSAT questions, answer keys, images, or other
copyrighted materials.

Public repository contents are synthetic artifacts, code, tests, schemas,
documentation, metadata, and evaluation outputs consistent with that
synthetic-first scope.
```

## `PROJECT_STATUS.md`

```md
# Project Status

## Current state

Milestone: lean OpenAI-primary synthetic LR baseline

The repository has been trimmed to emphasize the active OpenAI-primary
synthetic LR pipeline. Legacy OCR, text-ingest, and deprecated local-model
prototype paths have been removed from the active source tree, and related
tests have been retired from the active suite.

Current verified state:

- OpenAI is the active backend for the main workflow.
- Synthetic LR is the primary public pipeline.
- Multi-candidate synthetic LR orchestration is implemented.
- Deterministic payload validation and content-quality checks are active.
- Canonical mapping, review routing, and filesystem persistence are wired end to end.
- Batch generation, evaluation, and MLflow tracking remain active.
- The repository is in a lean cleanup state ahead of freezing `baseline_v1` and `eval_set_v1`.

## Test Status

The focused synthetic LR suite is currently green: 17 passed. The core lane, batch, cost-metrics, and review-routing tests now align with the current canonical schema and no longer depend on the retired `LSATInfo` model. [memory:1]

Current active test coverage includes:

- `tests/test_run_synthetic_lr_lane.py`
- `tests/test_run_synthetic_lr_batch.py`
- `tests/test_batch_cost_metrics.py`
- `tests/test_synthetic_lr_review_routing.py`

The test suite is intentionally lean. Duplicate or legacy-specific tests should be removed rather than preserved when they no longer represent a distinct production seam. [memory:1]

## Test Status

The current suite is green: 71 passed, 1 skipped. The active synthetic LR pipeline now uses the `RecordMetadata` canonical schema rather than the retired `LSATInfo` model, and the tests reflect that updated contract. [memory:1]

Active coverage includes:

- API record creation.
- Synthetic LR lane orchestration.
- Synthetic LR batch orchestration.
- Cost and latency aggregation.
- Content quality checks.
- Review routing.
- Validation and integration coverage. [memory:1]

The repository intentionally keeps the test surface lean. When a test no longer covers a distinct production seam, it should be merged or removed instead of retained as legacy duplication. [memory:1]


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
```

Targeted synthetic LR commands:

```bash
pytest -q tests/test_run_synthetic_lr_lane.py tests/test_run_synthetic_lr_batch.py tests/test_batch_cost_metrics.py
python -m src.normalize.run_synthetic_lr_batch
python -m src.evaluate.run_evaluation <batch_summary_path>
```

## Immediate next step

The next milestone is to freeze two things together:

- `baseline_v1` for the current known-good synthetic LR path,
- `eval_set_v1` as the fixed evaluation reference set.

Only after that freeze should older evaluation artifacts and historical run
clutter be reduced.

## Notes

- Existing evaluation JSON and Markdown reports are being kept temporarily as historical context.
- The repo is intentionally favoring leanness over preserving older prototype paths in-tree.
- Git history is the archive for removed legacy code.
- Status counts in documentation should be updated only when re-verified against the active suite.
```

## One cleanup note

Your current `PROJECT_STATUS.md` draft still mixes in older claims like OCR/text lanes being part of the same active first-class slice, plus leftover placeholder analysis text. That should be removed so the document reflects the now-trimmed synthetic-first repo shape.[2][3]

If you want, I can also provide a **paste-ready cleaned version of your existing `PROJECT_STATUS.md` only**, preserving more of your current wording while stripping outdated sections.
