# LSAT Multimodal Pipeline

An end-to-end pipeline for turning LSAT source material into canonical JSON records for downstream study, retrieval, review, and future RAG-based tutoring workflows.[web:326][cite:284]

## Project overview

This repository focuses on structured ingestion of LSAT content from text and image sources, normalization into a canonical nested record, validation, review-queue routing, and lightweight API access.[cite:284][memory:130] The current design favors a filesystem-first workflow and chunking before longer-context model changes, which keeps the system inspectable and modular while the pipeline is still evolving.[cite:130][web:334]

## Architecture

The codebase is organized by pipeline stage under `src/`:

- `src/ingest/` — simple manifest and loaders for text and (future) image sources.
- `src/ocr/` — OCR routing and text extraction for the image lane.
- `src/normalize/` — cleaning, splitting, and mapping into the canonical record.
- `src/classify/` — token counting and chunking utilities for classification strategies.
- `src/validate/` — record-level validation and review-queue routing.
- `src/persist/` — canonical Pydantic models and filesystem storage.
- `src/api/` — FastAPI app and ingest routes.[web:20][web:295]

The canonical record is defined with nested Pydantic models in `src/persist/models.py`, including `source`, `lsat`, `content`, `ocr`, `classification`, and `validation` sections.[web:293] The first completed vertical slice supports text-lane ingestion through `POST /ingest/ocr-text`, deterministic validation, review routing, and JSON persistence.[cite:284][memory:130]

### Current implementation state

- **Implemented and verified**
  - `src/classify/chunking.py` — token measurement and chunking strategy selection, covered by tests.[cite:130]
  - `src/normalize/canonical_mapper.py` — maps a manifest + text + segments into a `CanonicalRecord`.
  - `src/validate/confidence_checks.py` — validates section/text/answer-choice structure.
  - `src/validate/review_routing.py` — maps validation errors to review-queue destinations.
  - `src/persist/filesystem_store.py` — writes normalized and review records to filesystem.
  - `src/api/main.py`, `src/api/routes.py` — FastAPI app and `/ingest/ocr-text` endpoint.[cite:284]

- **Present but preliminary**
  - `src/normalize/run_text_lane.py`, `src/normalize/run_image_lane.py` — lane runners that will orchestrate full flows.
  - `src/ocr/ocr_router.py`, `src/ocr/extract_text.py` — OCR routing and extraction for the image lane.
  - `tests/test_text_lane.py`, `tests/test_image_lane.py`, `tests/test_validation.py` — tests that will grow as lanes mature.

- **Placeholder (not yet implemented)**
  - `src/classify/classify_document.py` — reserved for document-level classification orchestration; currently an empty stub.

## Folder structure (high level)

Key active folders:

- `src/api/` — FastAPI app and ingest routes.[web:20]
- `src/normalize/` — text cleaning, splitting, and canonical mapping.[memory:130]
- `src/classify/` — chunking utilities and future classifier orchestration.[cite:130]
- `src/validate/` — record validation and review destination selection.[cite:284]
- `src/persist/` — canonical models and filesystem storage.[memory:130]
- `tests/` — unit tests for chunking, mapping, validation, and lane behaviors.[memory:130]
- `data/normalized/records/` — accepted canonical records.[cite:284]
- `data/review_queue/` — records needing review, partitioned by reason (e.g., `malformed_split`).[memory:130]

## Completed vertical slice

The currently verified slice is:

`request body -> canonical mapping -> validation -> review routing -> filesystem persistence -> API response`.[cite:284]

Manual verification showed:

- A valid Logical Reasoning payload is written to `data/normalized/records/`.
- A malformed 3-choice payload is routed to `data/review_queue/malformed_split/` with structured validation errors.[memory:130]

## Setup

Use the repository root as the working directory:

```bash
cd ~/Documents/ds-project/01_data-science/projects/lsat-multimodal-pipeline
