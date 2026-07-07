# Project Status

## Current state


The text-lane vertical slice is complete and manually verified. The repository can ingest one Logical Reasoning text payload through the API, map it into the canonical record shape, validate it, route it, persist it, and return the saved record.


The synthetic Logical Reasoning lane is now a first-class slice that maps into the same canonical record + persistence flow as OCR/text lanes and includes a first-pass content-quality layer. Prompt v2 (per-flaw distractor role guidance + randomized correct-answer position) lifts the 100-item OpenAI batch to **19.32/25 mean** and **61% high-quality rate** (up from 18.66 / 36% on v1), judged by gpt-4o against the calibrated rubric.


## Verified on

Verified during the June 2026 working sessions when:

- `pytest` reported all deterministic tests passing
- FastAPI ingest endpoints responded successfully to health and ingest requests
- synthetic LR canonical and persistence tests passed
- synthetic content-quality tests and quality-lane integration tests passed[

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


## Milestone: LLM-as-judge evaluation calibrated on 100-item OpenAI batch (July 6, 2026)

The synthetic LR lane now has a first-class quality-scoring layer: an LLM-as-judge with a 5-dimension anchored rubric, batch-level MLflow logging, and Markdown report generation. The baseline was tuned through two calibration passes after discovering measurement bugs — the final numbers are defensible signal, not artifacts.

### What shipped

**Evaluation infrastructure**
- 5-dimension rubric in `src/evaluate/judge_rubric.py`: `argument_coherence`, `flaw_fidelity`, `question_stem_quality`, `distractor_plausibility`, `correct_answer_precision`
- Anchored scoring (1–5 with per-level definitions) plus explicit calibration rules ("score against real LSAT, not synthetic curve"; tie-break lower; reserve 5 for LSAT-indistinguishable items)
- `JudgeScore` Pydantic model with `total` and `is_high_quality` (threshold = 20/25)
- Per-record judge call with strict JSON output parsing and error-tolerant `JudgeResult` status (`scored` / `parse_error` / `runtime_error`)
- Batch runner in `src/evaluate/run_evaluation.py` with `synthetic_lr_evaluation` MLflow experiment, nested run per item, and aggregate metrics logged
- Prefix-match fallback in cost estimator to handle versioned OpenAI model IDs (`gpt-4o-2024-08-06` → `gpt-4o` pricing)

**Reporting**
- Markdown report renderer in `scripts/render_batch_report.py` with summary block, per-dimension means, per-config breakdown, and sample high/low items with judge notes
- Reports written to `data/reports/` alongside eval JSONs in `data/evaluations/`

### Verified

- 75 tests passing, 1 skipped
- End-to-end: 100-item batch evaluated on gpt-4o with anchored rubric
- Judge model: `gpt-4o-2024-08-06`
- Judge cost: $0.31 per 100 items
- Zero parse errors, zero runtime errors

### Calibration story (two bugs found, two fixes)

Initial baseline commit (`b67bfdf`) reported mean 13.89/25 with 0% high-quality. Investigation revealed two distinct measurement bugs:

**Bug 1 — judge prompt read flat keys** (fixed in `986e035`)
`build_judge_prompt` used `record_dict.get("stimulus", "")` but canonical records nest content under `record.content.stimulus`. Every judge prompt was sent with blank stimulus, question, and choices — the judge was hallucinating scores from `flaw_type` and `difficulty` labels alone.

Effect after fix: mean 13.89 → 22.68 on the same 100 items.

**Bug 2 — gpt-4o-mini rubber-stamped items** (fixed in `e846c37`)
Once the judge could see items, gpt-4o-mini at temperature 0.0 scored 100/100 items as high-quality with a 22–24 range (2-point spread). No discrimination.

Fix: rewrote `JUDGE_PROMPT_TEMPLATE` with explicit per-dimension anchors and calibration rules, and switched the judge to gpt-4o via `JUDGE_MODEL` env var.

Effect after fix: mean 22.68 → 18.66 with a 13–22 range (9-point spread), 36% high-quality rate.

### Final baseline (100-item OpenAI batch)

| Metric | Value |
|---|---|
| Items evaluated | 100 |
| Mean score | 18.66 / 25 |
| Median | 19.0 |
| Min / Max | 13 / 22 |
| High-quality rate (≥20) | 36% |

**Dimension means:**

| Dimension | Mean |
|---|---|
| Question stem quality | 3.98 |
| Correct answer precision | 3.87 |
| Flaw fidelity | 3.80 |
| Argument coherence | 3.68 |
| Distractor plausibility | 3.33 |

**Per-config breakdown:**

| Config | Avg score | High-quality rate |
|---|---|---|
| necessary_vs_sufficient_easy | 19.8 | 56% |
| causal_easy | 18.9 | 24% |
| causal_medium | 18.8 | 48% |
| necessary_vs_sufficient_medium | 17.1 | 16% |

### Next up (Session 1.5)

- Tighten distractor prompt guidance to produce flaw-adjacent wrong answers rather than generic critiques (target: lift `distractor_plausibility` from 3.33 → ≥3.8)
- Diagnose why `necessary_vs_sufficient_medium` lags all other configs (17.1 vs 18.8–19.8)
- Report renderer: swap `content.question` fallback to `content.question_stem` so reports stop showing "not captured" placeholder
- Optional: archive 163 legacy pre-refactor records (no `generation` metadata) into `data/legacy/` so future batches never sample from them

## Milestone: Distractor prompt v2 + position rotation (July 7, 2026)

### What shipped
- Prompt bumped `lr_flaw_v1` → `lr_flaw_v2` in `src/generate/synthetic_lr.py`
- Per-flaw distractor role guidance: CORRECT, TRAP-A (adjacent flaw), TRAP-B (right family wrong scope), TRAP-C (surface-plausible non-flaw), WEAK
- Randomized correct-answer position A–E per item via `correct_position` kwarg (fixes v1 position bias where 4/4 dry-run correct answers landed at A)
- `--n-per-config` CLI flag added to `src/normalize/run_synthetic_lr_batch.py`

### v2 vs v1 baseline (100-item OpenAI batch, judge = gpt-4o)
| Metric | v1 | v2 | Δ |
|---|---|---|---|
| Mean total | 18.66 | 19.32 | +0.66 |
| Median | — | 20.0 | — |
| High-quality rate | 36% | 61% | +25pp |
| Distractor plausibility | 3.33 | 3.58 | +0.25 |
| Flaw fidelity | — | 4.01 | — |
| Argument coherence | — | 3.75 | — |
| Question stem quality | — | 3.97 | — |
| Correct-answer precision | — | 4.01 | — |

### Artifacts
- Batch: `data/normalized/batches/batch_openai_25per_20260707_092511.json`
- Eval: `data/evaluations/eval_batch_openai_25per_20260707_092511_20260707_093043.json`
- Judge cost: $0.31 / 100 items; generation cost: $0.023 / 100 items

### Verified
- 75 tests pass, 1 skipped (Ollama opt-in)
- 100/100 items valid, 100/100 pass quality gate, 2 non-blocking `weak_argument_signals`
- Correct-answer positions verified rotating across A–E in dry-run

### Next up (Session 2)
- ReClor comparison harness — measure v2 prompt quality against an external LR benchmark
- Consider Session 1.6 distractor tightening only if ReClor gap suggests it

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

## Milestone: Larger real batch + DVC versioning (July 6, 2026)

### 100-item synthetic LR batch

Generated a 100-item synthetic LR batch to stress-test the API-backed pipeline at 5x the previous scale.

Results:
- **100/100 valid** (acceptance rate 1.0)
- **Cost**: $0.014909 (~$0.000149 per item)
- **Tokens**: 55,224 total (40,500 prompt + 14,724 completion)
- **Latency**: p95 3.85s per item, matching earlier smaller-batch p95
- **Runtime errors**: 0
- **Duration**: ~3.5 minutes total

All metrics captured in MLflow (run `09b88dafe553...`). Cost model in `MODEL_PRICING_USD_PER_MTOK` proved accurate to the dollar vs earlier smaller-batch extrapolation.

### DVC initialized

`data/normalized/records/` is now versioned by DVC:
- 300 canonical records tracked as one directory hash
- Local cache only (1.7 MB); no remote yet
- Un-tracked 21 records that had been committed to git in the initial commit before .gitignore covered them
- DVC analytics opted out

### Verified

- 58 tests passing, 1 skipped
- `dvc status` clean
- `git status` clean

### Next up

- Optional: configure a DVC remote (S3 / GDrive / external drive)
- Explore RC (Reading Comprehension) generation lane
- Consider `dvc.yaml` pipeline for reproducible batch stages