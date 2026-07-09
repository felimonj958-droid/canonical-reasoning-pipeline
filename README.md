# canonical-reasoning-pipeline

A synthetic-first pipeline for generating, validating, and versioning canonical
records of law-admissions-style logical reasoning (LR) and reading
comprehension (RC) content.

The project focuses on high-quality synthetic content, a strict canonical
record schema, deterministic validation, review-queue routing, and versioned
dataset releases. Ingestion of external text and image sources exists as
secondary infrastructure used for internal calibration only.

## API token setup

The FastAPI endpoints are protected with a static Bearer token read from the `API_TOKEN` environment variable.[web:507][web:508]

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

5. Call protected endpoints with the token in the `Authorization` header using the `Bearer` scheme:
   ```bash
   curl -X POST http://127.0.0.1:8000/ingest/ocr-text \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer ${API_TOKEN}" \
     -d @payload.json
   ```

If `API_TOKEN` is missing or the Bearer token does not match, protected endpoints will return an authorization error.[web:507][web:511]

### Trying the API in the browser

1. Start the server:

   ```bash
   python -m uvicorn src.api.main:app --reload
   ```

2. Open `http://127.0.0.1:8000/docs` in a browser.

3. Click **Authorize**, paste your `API_TOKEN` as the Bearer token, and hit **Authorize**.

4. Expand `POST /ingest/ocr-text`, click **Try it out**, and send a sample JSON payload.

Once the server is running and `API_TOKEN` is set, you can test the ingest endpoint either from `/docs` or with `curl`. A minimal payload like the example above will be accepted, validated, and routed into the `data/review_queue/` directory with `status="needs_review"` when required fields (stimulus, question stem, choices, etc.) are missing, which is expected for incomplete records.

Common responses from `POST /ingest/ocr-text`:

- `401 Unauthorized`: missing or incorrect `API_TOKEN` in the `Authorization` header.
- `422 Unprocessable Entity`: JSON body does not match the request schema (e.g., required fields missing).
- `200 OK` with `status="needs_review"`: record ingested but incomplete; routed into `data/review_queue/...`.

Ingested records that fail validation or are incomplete are persisted under `data/review_queue/` with a `status="needs_review"` payload, and are never promoted into `data/normalized/records/` without passing the same canonical validation used for synthetic runs.

## Quickstart

From repo root:

```bash
pytest -q
python -m src.normalize.run_synthetic_lr_batch
python -m uvicorn src.api.main:app --reload
```

Recommended reading order:

1. `PROJECT_STATUS.md` for the latest milestone and batch results
2. `data/reports/` for evaluation summaries
3. `src/normalize/run_synthetic_lr_batch.py` for the primary synthetic LR entrypoint

The synthetic LR batch is the current primary public workflow. API ingestion and OCR-related components remain secondary infrastructure.

## Docker

### Build locally

```bash
docker build -t canonical-reasoning-pipeline:local .
```

### Run locally

```bash
docker run --rm -p 8000:8000 --env-file .env canonical-reasoning-pipeline:local
```

Then open:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/openapi.json`

### Inspect the local image

```bash
docker image ls canonical-reasoning-pipeline:local
docker image inspect canonical-reasoning-pipeline:local
```

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

### Data & Evaluation Artifacts

- `data/evaluations/` contains JSON outputs from LLM-as-judge runs over synthetic LSAT-style items.
- `data/reports/` contains Markdown batch reports summarizing these evaluations.

These artifacts may reference LSAT-style quality standards and phrasing for comparison, but they do not embed or redistribute official LSAT questions, passages, answer keys, or images.

## Identity

The primary identity of this repository is:

- synthetic LR and RC content generation,
- canonical record mapping under a stable Pydantic schema,
- strict deterministic validation and review-queue routing,
- reproducible, versioned dataset releases via DVC,
- generation and acceptance tracking via MLflow,
- LLM-as-judge quality scoring on a calibrated 5-dimension rubric with Markdown reports.

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


### Latest baseline

100-item synthetic LR batch generated with gpt-4o-mini and evaluated by an
LLM judge (gpt-4o, anchored 5-dimension rubric):

- mean quality score: 18.66 / 25
- high-quality rate (≥ 20): 36%
- weakest dimension: distractor plausibility (3.33 / 5)
- strongest dimension: question stem quality (3.98 / 5)
- judge cost: $0.31 per 100 items

Latest report and eval JSON live under `data/reports/` and
`data/evaluations/`. Full milestone log in `PROJECT_STATUS.md`.

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


## Data versioning (DVC)

The canonical records dataset (`data/normalized/records/`) is versioned with DVC. Actual JSON files live in DVC's local cache; git tracks only the `.dvc` pointer file.

### Current dataset

- 300 canonical records across text-lane + synthetic-LR lanes
- ~1.1 MB total, hashed as one directory (`records.dvc`)
- Local cache only; no remote configured yet

### Working with the dataset

```bash
# Check status
dvc status

# After adding or regenerating records
dvc add data/normalized/records
git add data/normalized/records.dvc
git commit -m "data: <what changed>"

# To restore the dataset matching a specific commit
git checkout <sha>
dvc checkout
```

### What DVC does not track (yet)

- No remote storage — if you need to share the dataset across machines, set one up with `dvc remote add`
- No `dvc.yaml` pipeline — the batch script isn't a formal DVC stage yet

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

- `75 passed, 1 skipped` (live Ollama integration test is opt-in)

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
python -m src.normalize.run_synthetic_lr_batch
python -m uvicorn src.api.main:app --reload
```

Use `python -m src.normalize.run_synthetic_lr_batch` as the primary public entrypoint for synthetic LR generation. The API and ingestion/OCR routes are secondary infrastructure.

## Troubleshooting

A few common issues and how to interpret them:

- `401 Unauthorized` from API routes  
  The `Authorization` header is missing or the Bearer token does not match `API_TOKEN`.  
  - Ensure `.env` is loaded in your shell (`set -a; source .env; set +a`).  
  - Confirm `API_TOKEN` in `.env` matches what you paste into `/docs` → **Authorize** or pass via `curl` as `Authorization: Bearer ${API_TOKEN}`.[web:507][web:582]

- `422 Unprocessable Entity` from `POST /ingest/ocr-text`  
  The request body does not match the expected Pydantic model; FastAPI returns 422 when required fields are missing or have the wrong type.[web:579][web:580]  
  - Check the `detail` array in the JSON response — it lists which fields are missing or invalid (for example, `source_file`, `raw_text`, or `normalized_text`).  
  - Use `/docs` to inspect the request schema and adjust your JSON payload accordingly (e.g., include `source_file`, `raw_text`, and `normalized_text` for simple text-lane tests).

- `status="needs_review"` with a `saved_path` under `data/review_queue/...`  
  The record was ingested and validated, but is incomplete or failed canonical checks (for example, missing LR stimuli, question stem, or answer choices).  
  - This is expected for quick smoke-test payloads and for incomplete ingests.  
  - These records are not promoted to `data/normalized/records/` unless they pass the same validation as synthetic batches.

- `dvc status` shows `changed outs` for `data/normalized/records.dvc`  
  The canonical records directory has changed relative to the last DVC snapshot (new or modified JSON files).[web:523][web:593]  
  - If the changes are intentional and should ship, run:
    ```bash
    dvc add data/normalized/records
    git add data/normalized/records.dvc
    git commit -m "data: <what changed>"
    ```  
  - If not, revert local changes before running `dvc checkout` to restore the dataset for a previous commit.
  - `docker build` fails with `failed to read dockerfile: open Dockerfile: no such file or directory`  
  Ensure a file named `Dockerfile` exists in the repo root, or pass `-f <path>` explicitly when building.[web:609][web:610]

If you encounter other errors, start by checking the full JSON error body and the relevant section of this README (API token setup, MLflow, DVC, or ingestion) before changing code.

## Roadmap

Near-term:

- tighten distractor prompt guidance to lift `distractor_plausibility`
  score on the synthetic LR baseline
- diagnose the `necessary_vs_sufficient_medium` per-config gap
- add a comparison harness against a public LR/reasoning dataset
  (e.g. ReClor) for external calibration
- expose the pipeline behind a FastAPI service (`/generate`, `/evaluate`,
  `/health`)

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

## License and contributions

See `LICENSE` for usage terms.

This repository is currently maintained as a portfolio and research codebase. Small fixes and documentation improvements are welcome, but the roadmap and primary design direction are currently owner-driven.