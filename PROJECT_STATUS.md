# Project Status

## Current state

The text-lane vertical slice is complete and manually verified. The repository can ingest one Logical Reasoning text payload through the API, map it into the canonical record shape, validate it, route it, persist it, and return the saved record.[cite:284][memory:130]

The synthetic Logical Reasoning lane is now a first-class slice that maps into the same canonical record + persistence flow as OCR/text lanes and includes a first-pass content-quality layer.

## Verified on

Verified during the June 2026 working sessions when:

- `pytest` reported all deterministic tests passing
- FastAPI ingest endpoints responded successfully to health and ingest requests
- synthetic LR canonical and persistence tests passed
- synthetic content-quality tests and quality-lane integration tests passed[memory:130][cite:10]

## Working commands

From repo root:

```bash
cd ~/Documents/lsat-multimodal-pipeline
pytest -q
python -m uvicorn src.api.main:app --reload
## Synthetic Logical Reasoning lane

The synthetic Logical Reasoning lane now runs as a first-class local pipeline and is fully wired into canonical validation and persistence.[conversation_history:1]

Current flow:
`generate_synthetic_lr -> parse_synthetic_lr_output -> run_content_quality_checks -> map_synthetic_lr_to_record -> validate_record -> review_routing -> filesystem_store`.[conversation_history:1]

Implemented capabilities:
- Prompt builder with explicit `flaw_type` and `difficulty` control in `src/generate/synthetic_lr.py`.[conversation_history:1]
- Supported flaw families currently include:
  - `causal`
  - `necessary_vs_sufficient`.[conversation_history:1]
- Content-quality checks implemented in `src/generate/content_quality_checks.py`:
  - length checks,
  - meta-language detection,
  - LSAT-style question-stem checks,
  - argument-signal checks,
  - choice-quality checks.[conversation_history:1]
- Synthetic review routing now distinguishes:
  - `synthetic_structural`
  - `synthetic_low_quality`.[conversation_history:1]
- Batch harness implemented at `src/normalize/run_synthetic_lr_batch.py` with:
  - tiny config sweeps across flaw type and difficulty,
  - aggregate summary reporting,
  - per-item runtime error tolerance.[conversation_history:1]

### Real batch note

A first real local batch run completed successfully with the following summary:
- 2 valid records,
- 2 review records routed to `synthetic_structural`,
- no runtime errors,
- LSAT-style stem heuristic initially overfired and was then corrected to accept standard flaw stems such as “The reasoning in the argument is most vulnerable to criticism on the grounds that it…”.[conversation_history:1][web:76]

### Local hardware constraints

Synthetic generation currently runs locally through Ollama using `qwen3:8b`.[conversation_history:1] On a 16 GB machine, even tiny batches can take several minutes and require closing other heavy apps or unused local services to keep RAM usage manageable.[conversation_history:1]

Current practice:
- keep synthetic batches very small,
- keep persistence on for real probes,
- avoid repeated large runs during prompt/heuristic iteration.[conversation_history:1]

### Test status

Current local suite:
- `39 passed, 1 skipped`.[conversation_history:1]

Synthetic LR coverage now includes:
- prompt builder tests,
- canonical lane tests,
- metadata tests,
- persistence tests,
- review routing tests,
- content-quality tests,
- batch harness stub tests,
- question-style heuristic tests.[conversation_history:1]

## Synthetic LR status

The synthetic LSAT Logical Reasoning lane is now working end to end for local generation, parsing, quality screening, canonical mapping, validation, and persistence.

Current pipeline:
`generate_synthetic_lr -> clean_synthetic_lr_output -> parse_synthetic_lr_output -> run_content_quality_checks -> map_synthetic_lr_to_record -> validate_record -> review_routing -> filesystem_store`

Implemented features:
- flaw-controlled synthetic prompt generation (`causal`, `necessary_vs_sufficient`)
- difficulty-controlled generation (`easy`, `medium`, `hard`)
- content-quality heuristics:
  - length checks
  - meta-language detection
  - LSAT-style stem checks
  - argument-signal checks
  - choice-quality checks
- output cleaning for streamed local model artifacts:
  - strips ANSI escape codes
  - strips `Thinking...` / `...done thinking.` preamble text
- synthetic review routing:
  - `synthetic_structural`
  - `synthetic_low_quality`

### Current corpus state

The synthetic corpus currently contains a mix of:
- scaffold synthetic records used for pipeline/persistence testing (for example, records with stimulus `A simple argument.`)
- a small number of genuine LSAT-like flaw items generated locally and persisted successfully

Scaffold records should not be treated as training-quality synthetic data.

### Local runtime constraints

Synthetic generation currently runs locally via Ollama using `qwen3:8b`.
On a 16 GB machine, generation is functional but slow and memory-sensitive.
Current working practice:
- use very small batches,
- prefer reuse/inspection of recent outputs over rerunning,
- close heavy apps and unused services before generation.

### Test status

Current local suite:
- `41 passed, 1 skipped`
 
## API-backed generation milestone

The provider-agnostic `LLMClient` layer is now in place with two
working backends:

- `OllamaClient` (local, default)
- `OpenAIClient` (API, gated on `OPENAI_API_KEY`)

Backend selection happens via `LLM_BACKEND` and is applied uniformly
across the synthetic LR lane and batch harness. Each generated record
records the active backend, model, token counts, and latency under
`record.generation`.

### Test status

Current local suite:
- `45 passed, 1 skipped`

New coverage:
- OpenAI client generates + records metadata (mocked SDK)
- OpenAI client forwards call parameters (model, temperature,
  max_tokens, system, extra)
- OpenAI client raises a clear error when `OPENAI_API_KEY` is missing
- Factory dispatches to OpenAIClient on `LLM_BACKEND=openai`

### Deferred

- Anthropic backend (same pattern; add `anthropic_client.py` + factory
  branch when needed)
- MLflow around `run_synthetic_lr_batch` for run tracking
- DVC init for `data/normalized/records/`


## Milestone: API-backed generation + MLflow tracking (July 2026)

The synthetic LR lane now runs against the OpenAI API (gpt-4o-mini) via a pluggable LLMClient protocol, and every batch is instrumented with MLflow.

### What shipped

**Generation backends**
- `LLMClient` protocol in `src/llm_client/base.py` with `GenerationRequest`/`GenerationResponse` dataclasses
- `OllamaClient` (local) and `OpenAIClient` (API) implementations with lazy SDK imports + cached clients
- Factory `get_llm_client()` dispatches on `LLM_BACKEND` env var (defaults to ollama)
- `GenerationMeta` recorded on every `CanonicalRecord` (backend, model, tokens, latency)
- direnv + `.env` for local env-var management (`.env.example` committed as template)

**Experiment tracking**
- `src/tracking/MLflowTracker` context manager with lazy mlflow import + `TRACKING_DISABLED` no-op mode
- `run_synthetic_lr_batch` wrapped with parent-run + nested-run-per-config instrumentation
- Batch summaries persisted to `data/normalized/batches/` and logged as run artifacts
- Git SHA tagged on every run for code traceability

### Verified

- 49 tests passing, 1 skipped (Ollama integration, opt-in)
- Live smoke: 4/4 valid via gpt-4o-mini, ~$0.0006 total cost, ~2.3s latency per item
- MLflow UI confirms parent + 4 nested runs per batch with expected params, metrics, and artifacts

### Comparison vs local baseline

| | Qwen 3 8B (Ollama) | gpt-4o-mini (OpenAI) |
|---|---|---|
| Valid records (of 4) | 2 | 4 |
| Routed to review | 2 | 0 |
| Runtime | multi-minute | ~10s |
| Cost | free (local) | ~$0.0006 |

### Next up

- Pipe `GenerationMeta` (prompt_tokens, completion_tokens, latency_ms) into MLflow metrics
- Larger real batch (`n_per_config=5–10`) with cost visibility
- DVC init on `data/normalized/records/`