
## PROJECT_STATUS

```md
# Project Status
•	OpenAI is the active runtime path.
•	The full suite is  83 passed, 1 skipped .
•	Synthetic LR is the primary workflow.

## Current state

Milestone: OpenAI-primary synthetic LR orchestration

The synthetic LR lane now supports multi-candidate generation and deterministic selection before canonical mapping. The batch harness threads `num_candidates` through to the lane, and batch artifacts record candidate-level diagnostics for traceability.

Current verified state:
- OpenAI is the active demo and batch backend.
- Ollama is no longer part of the active runtime path.
- DVC pipeline wiring is complete.
- Best-of-N synthetic LR orchestration is complete.
- The current full suite is `83 passed, 1 skipped`.

## Verified artifacts

- `tests/test_run_synthetic_lr_lane.py`
- `tests/test_run_synthetic_lr_batch.py`
- `tests/test_run_synthetic_lr_batch_persist.py`

## Repository status

The text-lane vertical slice is complete and manually verified. The repository can ingest one Logical Reasoning text payload through the API, map it into the canonical record shape, validate it, route it, persist it, and return the saved record.

The synthetic Logical Reasoning lane is now a first-class slice that maps into the same canonical record + persistence flow as OCR/text lanes and includes a first-pass content-quality layer. Prompt v2, with per-flaw distractor role guidance and randomized correct-answer position, lifted the 100-item OpenAI batch to **19.32/25 mean** and **61% high-quality rate**, up from **18.66/25** and **36%** on v1, judged by gpt-4o against the calibrated rubric.

## Verified on

Verified during the June and July 2026 working sessions when:

- `pytest` reported all deterministic tests passing.
- FastAPI ingest endpoints responded successfully to health and ingest requests.
- synthetic LR canonical and persistence tests passed.
- synthetic content-quality tests and quality-lane integration tests passed.
- batch aggregation and persistence tests passed after the OpenAI-primary refactor.

## Working commands

From repo root:

```bash
cd ~/Documents/canonical-reasoning-pipeline
pytest -q
python -m src.normalize.run_synthetic_lr_batch
python -m uvicorn src.api.main:app --reload

•	OpenAI is the active runtime path.
•	The full suite is  83 passed, 1 skipped .
•	Synthetic LR is the primary workflow.