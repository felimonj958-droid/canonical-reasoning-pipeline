# canonical-reasoning-pipeline

A synthetic-first canonical reasoning pipeline for generating, validating, routing, persisting, and evaluating structured reasoning records. The active workflow is OpenAI-primary and centered on stable canonical record contracts rather than legacy OCR-ingest assumptions.

## What this project does

This repository provides an end-to-end pipeline for synthetic Logical Reasoning item generation and evaluation:

1. Generate or receive reasoning content.
2. Validate the payload structure and content quality.
3. Map the payload into a canonical record.
4. Route the record to normalized storage or the review queue.
5. Persist records and batch metadata.
6. Evaluate saved records with an LLM judge.
7. Track batch generation and evaluation runs with MLflow.

## Repository structure

The repo is organized around a small number of live runtime layers:

- `src/generate/` — synthetic LR generation, parsing, validation, and content-quality checks.
- `src/normalize/` — lane orchestration, canonical mapping, and batch generation.
- `src/validate/` — canonical validation and review routing.
- `src/persist/` — canonical record models and filesystem persistence.
- `src/evaluate/` — LLM-as-judge scoring and batch evaluation.
- `src/api/` — FastAPI service surface for record creation.
- `src/llm_client/` — backend abstraction for model calls.
- `src/tracking/` — MLflow tracking wrapper and Git SHA helper.
- `tests/` — test modules mapped to live runtime seams.
- `data/` — normalized records, batch summaries, evaluation outputs, reports, review queue items, and samples.

## Core dependency chain

The live synthetic LR path runs in this order:

`src.generate -> src.normalize -> src.validate -> src.persist`

The evaluation path runs in parallel:

`src.evaluate -> src.llm_client -> src.tracking`

The API reuses the same canonical pipeline code:

`src.api -> src.normalize / src.validate / src.persist`

## Active runtime flow

The main lane executes as:

`generate_synthetic_lr -> clean_synthetic_lr_output -> parse_synthetic_lr_output -> validate_synthetic_lr_payload -> run_content_quality_checks -> map_synthetic_lr_to_record -> validate_record -> choose_destination -> save_record`

The batch runner wraps the lane and writes a summary:

`run_synthetic_lr_batch -> run_synthetic_lr_lane -> MLflowTracker -> batch summary JSON`

The evaluation runner consumes batch summaries and saved records:

`evaluate_batch -> _load_records_from_batch_summary -> judge_record -> aggregate_scores -> MLflowTracker`

## API surface

The service layer exposes a small authenticated FastAPI app for creating canonical records.

Main routes:
- `GET /` — service status.
- `GET /health` — application health.
- `GET /records/health` — records-router health.
- `POST /records` — create and persist a canonical record.

The API expects an `API_TOKEN` bearer token in the request header.

Example:
```bash
-H "Authorization: Bearer $API_TOKEN"
```

## Data layout

The `data/` directory contains the main artifacts produced and consumed by the pipeline:

- `data/normalized/records/` — canonical saved records.
- `data/normalized/batches/` — batch summaries from generation runs.
- `data/review_queue/` — routed review items, split by reason.
- `data/evaluations/` — JSON outputs from judge evaluation runs.
- `data/reports/` — human-readable evaluation reports.
- `data/sample_text/` — small sample text artifacts.

The most important data dependencies are:

- batch summaries point to saved records,
- evaluation files depend on batch summaries and normalized records,
- reports summarize evaluation output,
- review queue files capture items rejected from normalized storage.

## Evaluation workflow

Evaluation is handled by `src/evaluate/` and is centered on a judge rubric plus per-record scoring.

The evaluation loop:
- reads a batch summary,
- loads each record referenced by `saved_path`,
- scores each record with the judge,
- aggregates score totals, dimensions, and flaw-type breakdowns,
- logs metrics and artifacts to MLflow,
- writes a JSON evaluation artifact to `data/evaluations/`.

The most important evaluation signal right now is `distractor_plausibility`, which has been the most consistent weak point in recent smoke runs.

## Test strategy

The test suite is intentionally lean and organized by live production seam rather than by implementation detail.

Examples of coverage:
- API record creation and routing.
- Synthetic LR generation and parsing.
- Lane orchestration and batch summaries.
- Validation and review routing.
- Persistence behavior.
- LLM judge parsing and aggregation.
- MLflow tracking behavior.
- OpenAI client behavior.

The test layout is documented in `tests/README.md`.

## Current stage

The repository is in a lean **OpenAI-primary synthetic LR stage**:

- synthetic LR generation is the main public workflow,
- the canonical record pipeline is wired end to end,
- multi-candidate lane selection is implemented,
- batch generation, evaluation, and MLflow tracking are working,
- DVC is in use for canonical-record reproducibility work,
- legacy OCR/text-ingest and deprecated Ollama-era runtime paths are no longer part of the active repo surface.

## Quickstart

From the repo root:

```bash
pytest -q
python -m src.normalize.run_synthetic_lr_batch
python -m src.evaluate.run_evaluation <batch_summary_path>
python -m uvicorn src.api.main:app --reload
```

## API token setup

The FastAPI endpoints are protected with a static Bearer token read from the `API_TOKEN` environment variable.

```bash
cp .env.example .env
set -a
source .env
set +a
uvicorn src.api.main:app --reload
```

## Docker

Build locally:

```bash
docker build -t canonical-reasoning-pipeline:local .
```

Run locally:

```bash
docker run --rm -p 8000:8000 --env-file .env canonical-reasoning-pipeline:local
```

## Generation backend

Synthetic generation runs through a provider-agnostic `LLMClient` layer under `src/llm_client/`.

Current backend:
- `openai`

Key environment variables:
- `LLM_BACKEND`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_BASE_URL`
- `JUDGE_MODEL`

## Experiment tracking

Synthetic-generation batches and evaluation runs are tracked in MLflow. Runs are stored locally under `mlruns/` and are not committed to Git.

Tracking includes:
- parent batch runs,
- nested per-config runs,
- generation-metric aggregation,
- evaluation metrics,
- token usage,
- estimated cost,
- persisted artifacts.

## Documentation map

If you want more detail, read these in order:

1. `src/README.md`
2. `src/normalize/README.md`
3. `src/evaluate/README.md`
4. `src/api/README.md`
5. `data/README.md`
6. `data/evaluations/README.md`
7. `tests/README.md`

## Notice and scope

This project is not affiliated with, endorsed by, or sponsored by LSAC, and it does not redistribute official LSAT questions, answer keys, images, or other copyrighted materials.

Public repository contents are synthetic artifacts, code, tests, schemas, documentation, metadata, and evaluation outputs consistent with that synthetic-first scope.
