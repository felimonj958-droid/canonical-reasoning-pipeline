

## What changed

Current repo state is leaner than the pasted docs suggest: the legacy OCR/text-ingest lane was retired from the active source tree, related tests were removed, and the active repo now centers on the OpenAI-primary synthetic LR pipeline plus the FastAPI surface that remains in `src/api/`. The full suite also moved from the older `83 passed, 1 skipped` state to `78 passed, 1 skipped`, so the status numbers in both docs are stale.

The docs should now emphasize:
- OpenAI-primary synthetic LR as the main public workflow.
- Lean active code surface after removing legacy OCR/text-ingest and Ollama paths.
- Evaluation reports kept temporarily as context until baseline v1 and eval set v1 are freshly frozen.

## README rewrite


```md
# canonical-reasoning-pipeline

A synthetic-first pipeline for generating, validating, and versioning canonical
records for law-admissions-style reasoning content.

The active repository is centered on an OpenAI-primary synthetic Logical
Reasoning (LR) workflow: generation, validation, canonical mapping,
persistence, evaluation, and experiment tracking. Legacy OCR, raw text
ingestion, and deprecated local-model prototype paths have been removed from
the active codebase so the repository reflects the current reproducible
baseline more clearly.

## Current stage

The repository is in a lean **OpenAI-primary synthetic LR stage**:

- synthetic LR generation is the primary public workflow,
- the canonical record pipeline is wired end to end,
- batch generation, evaluation, and MLflow tracking are working,
- DVC is in use for core canonical-record data artifacts,
- legacy local-model and older OCR/text-ingest prototype paths have been
  retired from the active repo surface.

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

1. `PROJECT_STATUS.md` for the latest milestone state.
2. `data/reports/` for evaluation summaries.
3. `src/normalize/run_synthetic_lr_batch.py` for the primary synthetic LR entrypoint.

## Active repository scope

The active repository focuses on:

- synthetic LR generation,
- canonical mapping and persistence,
- validation and review routing,
- evaluation and report generation,
- MLflow-tracked experimentation,
- DVC-backed reproducibility for canonical record artifacts,
- FastAPI endpoints for the current ingestion surface.

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

## Primary lane: synthetic Logical Reasoning

The synthetic LR lane is the current first-class flow:

`generate_synthetic_lr -> clean_synthetic_lr_output -> parse_synthetic_lr_output -> run_content_quality_checks -> map_synthetic_lr_to_record -> validate_record -> review_routing -> filesystem_store`

Implemented capabilities include:

- prompt-driven LR generation with controlled flaw type and difficulty,
- structural parsing and validation,
- content-quality heuristics,
- canonical mapping into a stable Pydantic schema,
- review routing for low-quality or structurally invalid outputs,
- persistence of accepted records under `data/normalized/records/`,
- batch generation through `src/normalize/run_synthetic_lr_batch.py`,
- evaluation through LLM-as-judge scoring and Markdown reporting.

## Generation backend

Synthetic generation runs through a provider-agnostic `LLMClient` layer under
`src/llm_client/`. The active backend in this repo stage is:

- `openai` — the primary backend for the current baseline and demo workflow.

Environment variables:

| Variable | Applies to | Purpose |
|---|---|---|
| `LLM_BACKEND` | all | Select backend. Default: `openai`. |
| `OPENAI_API_KEY` | openai | Required. |
| `OPENAI_MODEL` | openai | Default model. |
| `OPENAI_BASE_URL` | openai | Optional OpenAI-compatible endpoint. |

## Experiment tracking

Synthetic-generation batches are tracked in MLflow. Runs are stored locally
under `mlruns/` (gitignored).

Each batch records:
- parent-level batch metadata and acceptance metrics,
- nested per-config metrics,
- summary artifacts for later inspection and comparison.

## Data versioning

Canonical record artifacts are tracked with DVC-backed data management where
appropriate, while evaluation outputs and reports remain in-repo for now as
context and prior art.

Current evaluation and report artifacts are being kept temporarily. After a
fresh `baseline_v1` and `eval_set_v1` are generated and documented, older
historical artifacts can be reduced for a cleaner long-term repo surface.

## Architecture

The active codebase is organized by pipeline stage under `src/`:

- `src/api/` — FastAPI app and routes,
- `src/classify/` — classification and chunking utilities,
- `src/evaluate/` — judge rubric, scoring, and evaluation runs,
- `src/generate/` — synthetic LR generation and quality checks,
- `src/llm_client/` — backend abstraction and OpenAI client,
- `src/normalize/` — canonical mapping and synthetic batch orchestration,
- `src/persist/` — canonical Pydantic models and filesystem storage,
- `src/tracking/` — MLflow tracking helpers,
- `src/validate/` — validation and review routing.

Key data folders:

- `data/normalized/records/` — accepted canonical records,
- `data/review_queue/` — records routed for review,
- `data/evaluations/` — evaluation JSON outputs,
- `data/reports/` — human-readable evaluation summaries.

## Tests

Current local suite:

- `78 passed, 1 skipped`

Coverage includes:

- synthetic LR generation and parsing,
- canonical mapping and persistence,
- evaluation and batch aggregation,
- metadata and quality-lane tests,
- validation and review routing,
- API-facing active behaviors.

## Roadmap

Near-term:

- freeze `baseline_v1`,
- freeze `eval_set_v1`,
- run a fresh evaluation against the frozen pair,
- reduce old evaluation artifacts after the new baseline is documented.

Medium-term:

- expand LR flaw families and difficulty tiers,
- strengthen evaluation and comparison reporting,
- expose the pipeline through a tighter public service surface.

Longer-term:

- add external calibration/comparison lanes without changing the synthetic-first
  identity,
- explore broader reasoning-task extensions only after the LR baseline is fully
  frozen and documented.

## Notice and scope

This project is not affiliated with, endorsed by, or sponsored by LSAC, and it
does not redistribute official LSAT questions, answer keys, images, or other
copyrighted materials. Public repository contents are synthetic artifacts, code,
tests, schemas, documentation, metadata, and evaluation outputs consistent with
that synthetic-first scope.
```

## PROJECT_STATUS rewrite

Use this as the updated `PROJECT_STATUS.md`:

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
- The synthetic LR lane is the primary public pipeline.
- Legacy OCR/text-ingest and Ollama-era paths are no longer part of the active repo surface.
- The current full suite is `78 passed, 1 skipped`.
- The repository is in a lean cleanup state ahead of freezing `baseline_v1` and `eval_set_v1`.

## Repository status

The active repository now centers on one clear path:

- synthetic LR generation,
- canonical mapping,
- deterministic validation,
- review routing,
- filesystem persistence,
- evaluation and report generation,
- MLflow-tracked experimentation,
- DVC-aware reproducibility work around canonical artifacts.

This makes the repo easier to read as a portfolio project and reduces drift
between the documented system and the actual runtime surface.

## Validation

Verified in the current cleanup state when:

- `pytest -q` passed with `78 passed, 1 skipped`,
- the active synthetic LR modules remained intact after source trimming,
- the FastAPI app remained part of the active codebase,
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
```

## Final pass

The biggest correction is conceptual: remove claims that OCR/text ingestion still exists as active secondary infrastructure, because your trimmed repo no longer supports that story cleanly. The second big correction is numerical: update every stale suite count and milestone statement to the current state.
