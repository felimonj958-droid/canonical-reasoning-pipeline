# canonical-reasoning-pipeline

A synthetic-first pipeline for generating, validating, and versioning canonical
records of law-admissions-style logical reasoning (LR) and reading
comprehension (RC) content.

The project focuses on high-quality synthetic content, a strict canonical
record schema, deterministic validation, review-queue routing, and versioned
dataset releases. Ingestion of external text and image sources exists as
secondary infrastructure used for internal calibration only.

## Notice and scope

This project is **not affiliated with, endorsed by, or sponsored by LSAC**, and
does not redistribute official LSAT questions, answer keys, images, or other
copyrighted materials. All content in the public repository is either
synthetically generated, code, schemas, tests, documentation, or dataset
release notes.

- Public artifacts: synthetic records, code, schemas, prompts that do not
  embed official text, validators, tests, documentation, DVC metadata, and
  release notes.
- Private and local-only: any official LSAC/LSAT text or images, OCR outputs
  of official material, answer keys, and any calibration corpora derived from
  official items.

References to "LR" and "RC" in this repository describe the general genre of
logical reasoning and reading comprehension tasks, not any specific
proprietary exam.

## Identity

The primary identity of this repository is:

- synthetic LR and RC content generation,
- canonical record mapping under a stable Pydantic schema,
- strict deterministic validation and review-queue routing,
- reproducible, versioned dataset releases via DVC,
- generation and acceptance tracking via MLflow.

Public reasoning datasets (Hugging Face, GitHub) are treated as **secondary**:
they exist as external calibration and comparison lanes, not as the repo's
main product. This repo's craftsmanship is the synthetic canonical corpus
adjacent to those datasets, not a wrapper around them.

## Primary lane: synthetic Logical Reasoning

The synthetic LR lane is the current first-class flow:

`generate_synthetic_lr -> clean_synthetic_lr_output -> parse_synthetic_lr_output
-> run_content_quality_checks -> map_synthetic_lr_to_record -> validate_record
-> review_routing -> filesystem_store`

Implemented capabilities:

- prompt builder with explicit `flaw_type` and `difficulty` control
- supported flaw families: `causal`, `necessary_vs_sufficient`
- supported difficulties: `easy`, `medium`, `hard`
- output cleaning for local model artifacts (ANSI escapes, `Thinking...`
  preambles)
- structural validation (labels, counts, non-empty and duplicate checks)
- content-quality heuristics:
  - length checks
  - meta-language detection
  - LR-style question-stem checks
  - argument-signal checks
  - choice-quality checks
- canonical mapping with `source.modality = "generated_text"` and
  `reasoning.section = "logical_reasoning"`
- review routing with dedicated synthetic destinations:
  - `data/review_queue/synthetic_structural/`
  - `data/review_queue/synthetic_low_quality/`
- filesystem persistence for accepted records under
  `data/normalized/records/`
- batch harness at `src/normalize/run_synthetic_lr_batch.py` for tiny sweeps
  across flaw type and difficulty, with aggregate summary reporting and
  per-item runtime error tolerance

## Generation backends

Synthetic generation runs through a provider-agnostic `LLMClient` layer
under `src/llm_client/`. The active backend is selected at runtime via
the `LLM_BACKEND` environment variable.

Supported backends:

- `ollama` (default) — local generation via the Ollama runtime. Intended
  for offline experimentation on constrained hardware.
- `openai` — OpenAI Chat Completions API. Intended as the default for
  real batches when local runtime is impractical. Also compatible with
  OpenAI-compatible providers (Together, Groq, Fireworks, local vLLM)
  via `OPENAI_BASE_URL`.

Environment variables:

| Variable | Applies to | Purpose |
|---|---|---|
| `LLM_BACKEND` | all | Selects backend (`ollama` \| `openai`). Default: `ollama`. |
| `OLLAMA_MODEL` | ollama | Default model. Default: `qwen3:8b`. |
| `OLLAMA_HOST` | ollama | Optional Ollama host URL. |
| `OPENAI_API_KEY` | openai | Required. |
| `OPENAI_MODEL` | openai | Default model. Default: `gpt-4o-mini`. |
| `OPENAI_BASE_URL` | openai | Optional; target an OpenAI-compatible API. |

Every synthetic record's `record.generation` field captures the backend
and model that actually produced it, along with token counts and
latency, so batches remain reproducible and comparable across backends.

Additional API backends (Anthropic, Together, DeepSeek) can be
registered in `src/llm_client/__init__.py` following the same pattern.

## Experiment tracking (MLflow)

Every synthetic-generation batch is tracked in MLflow. Runs are stored locally under `mlruns/` (gitignored) — no server required.

### What's tracked

Each `run_synthetic_lr_batch` invocation creates:

- **One parent run** per batch, named `batch_<backend>_<n>per_<timestamp>`
  - Params: `backend`, `model`, `n_per_config`, `num_configs`, `config_names`, `persist`
  - Tags: `git_sha`, `backend`, `pipeline=synthetic_lr`
  - Metrics: `total_items`, `total_valid`, `total_needs_review`, `total_runtime_errors`, `acceptance_rate`
  - Artifact: the batch summary JSON (`data/normalized/batches/<run_name>.json`)
- **One nested run per config** (e.g., `causal_easy`, `necessary_vs_sufficient_medium`)
  - Tags: `flaw_type`, `difficulty`
  - Metrics: `lane_items`, `lane_valid`, `lane_needs_review`, `lane_runtime_errors`, `lane_quality_ok`, `lane_acceptance_rate`

### Running a tracked batch

```bash
python -m src.normalize.run_synthetic_lr_batch
```

### Viewing runs

```bash
# CLI: list experiments and runs
mlflow experiments search
mlflow runs list --experiment-id <id>

# UI: browse runs in a browser
mlflow ui --backend-store-uri file:./mlruns --port 5001
# then open http://localhost:5001
```

Note: macOS uses port 5000 for AirPlay Receiver by default, so we use 5001.

### Disabling tracking

For tests, CI, or ad-hoc runs where you don't want to write to `mlruns/`:

```bash
TRACKING_DISABLED=1 python -m src.normalize.run_synthetic_lr_batch
```

Or programmatically: `run_synthetic_lr_batch(..., track=False)`.


## Canonical record

The canonical record is defined with nested Pydantic models in
`src/persist/models.py` and includes `source`, `reasoning`, `content`, `ocr`,
`classification`, and `validation` sections.

Every accepted record, whether synthetic or ingested, is required to conform
to the same schema and pass the same `validate_record()` and
`choose_destination()` logic before persistence.

## Secondary lane: ingestion

Ingestion of external text and image sources exists as secondary
infrastructure and is used for internal calibration only. It is not the
public product of this repository.

The ingestion vertical slice supports:

- text-lane ingestion via `POST /ingest/ocr-text`
- OCR routing and text extraction for image sources
- normalization, cleaning, splitting, and canonical mapping
- deterministic validation, review routing, and JSON persistence

Any records derived from private or copyrighted source material are handled
locally and are never persisted into public dataset releases.

## Architecture

The codebase is organized by pipeline stage under `src/`:

- `src/generate/` — synthetic LR generation, output cleaning, parsing, and
  content-quality checks
- `src/llm_client/` — provider-agnostic LLM backends (planned: API-backed
  clients + Ollama)
- `src/normalize/` — cleaning, splitting, canonical mapping, and batch
  harnesses
- `src/classify/` — token counting and chunking utilities
- `src/validate/` — record-level validation and review-queue routing
- `src/persist/` — canonical Pydantic models and filesystem storage
- `src/ingest/` — manifests and loaders for text and image sources
  (secondary)
- `src/ocr/` — OCR routing and text extraction for the image lane
  (secondary)
- `src/api/` — FastAPI app and ingest routes (secondary)

Key data folders:

- `data/normalized/records/` — accepted canonical records
- `data/review_queue/malformed_split/` — ingest records needing review
- `data/review_queue/synthetic_structural/` — structurally invalid synthetic
  outputs
- `data/review_queue/synthetic_low_quality/` — synthetic outputs failing
  content-quality heuristics

## Tests

Current local suite:

- `41 passed, 1 skipped` (live Ollama integration test is opt-in)

Coverage includes:

- chunking, mapping, validation, and ingest lane tests
- synthetic parser, structural validator, and canonical lane tests
- synthetic persistence tests
- synthetic content-quality tests
- synthetic quality-lane integration tests
- prompt builder, metadata, review routing, batch harness stub, and
  question-style heuristic tests

## Working commands

From repo root:

```bash
cd ~/Documents/canonical-reasoning-pipeline
pytest -q
python -m uvicorn src.api.main:app --reload
```

## Roadmap

Near-term:

- introduce `src/llm_client/` provider-agnostic layer and route synthetic LR
  through it
- wire MLflow around the synthetic LR batch harness to track params,
  acceptance metrics, and batch artifacts
- add DVC tracking for `data/normalized/records/` and formalize dataset
  snapshots

Medium-term:

- expand synthetic LR flaw families and difficulty tiers
- introduce synthetic Reading Comprehension generation under the same
  canonical schema and validation pipeline
- prepare a first synthetic dataset release with a documented data card

Longer-term:

- plug in public reasoning datasets as external calibration and comparison
  lanes without changing the primary synthetic identity
- explore human-response modeling on top of tracked generation metrics

## Corpus note

The current synthetic corpus is a mix of:

- scaffold records used for pipeline and persistence testing (for example,
  records with stimulus `A simple argument.`)
- a small number of genuine LR-style flaw items generated locally and
  persisted successfully

Scaffold records are not training-quality synthetic data and are excluded
from any dataset release.