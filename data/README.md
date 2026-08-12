# Data Folder Guide

This folder contains the project’s canonical artifacts, batch summaries, evaluation outputs, review-queue items, and lightweight samples used for development and inspection. The active workflow is synthetic-first and OpenAI-primary, so most important artifacts flow through `data/normalized`, `data/evaluations`, and `data/reports`.

## Folder map

### `data/normalized/records/`

Canonical record JSON files saved by the pipeline after validation and destination routing. These are the primary durable artifacts for the synthetic LR workflow.

Depends on:
- `src.normalize.run_synthetic_lr_lane`
- `src.api.routes`
- `src.persist.filesystem_store`

Produced by:
- `python -m src.normalize.run_synthetic_lr_batch`
- API requests to `POST /records`

Related files:
- `data/normalized/records.dvc` tracks the directory with DVC.
- `data/normalized/records/.gitkeep` keeps the folder present in Git.

### `data/normalized/batches/`

Batch summary JSON files created by the synthetic batch runner. These summarize each generation batch and include per-item results, saved paths, counts, and generation metrics.

Depends on:
- `src.normalize.run_synthetic_lr_batch`

Consumed by:
- `src.evaluate.run_evaluation`

Typical command:
```bash
python -m src.normalize.run_synthetic_lr_batch
```

### `data/review_queue/`

Records routed for manual review instead of normalized storage. This folder is split by review reason.

Subfolders:
- `malformed_split/` — structurally malformed or split-output cases.
- `missing_fields/` — records missing required content or fields.

Depends on:
- `src.persist.filesystem_store`
- `src.validate`
- `src.normalize.run_synthetic_lr_lane`

Produced by:
- generation or API flows when validation fails or the record is routed to review.

### `data/evaluations/`

JSON outputs from LLM-as-judge evaluation runs. These store aggregate metrics, per-record scores, token usage, latency, and cost estimates.

Depends on:
- `src.evaluate.run_evaluation`
- `src.evaluate.llm_judge`

Consumed by:
- manual analysis
- reporting and comparison workflows

Typical command:
```bash
python -m src.evaluate.run_evaluation <batch_summary_path> [limit]
```

### `data/reports/`

Human-readable Markdown evaluation reports. These are older or companion summaries for batch evaluation runs.

Depends on:
- reporting or documentation workflows
- older evaluation runs kept for reference

### `data/sample_text/`

Small sample text artifacts used for demonstrations or test fixtures.

Current files:
- `sample_generated_text.txt`
- `sample_reasoning_image.txt`

## Dependency flow

The main pipeline flow is:

`generation -> validation -> routing -> persistence -> batch summary -> evaluation -> report`

More concretely:

1. Synthetic generation creates candidate reasoning items.
2. Validation checks structure and content quality.
3. Records are routed to normalized storage or the review queue.
4. Batch summaries capture what was saved.
5. Evaluation reads batch summaries and loads the saved record JSON files.
6. Evaluation outputs are written to `data/evaluations`.
7. Human-readable reports are stored in `data/reports`.

## Commands

### Inspect the folder tree
```bash
find data -maxdepth 3 -print | sort
```

If `tree` is installed:
```bash
tree data -a -L 3
```

### Show directory sizes
```bash
du -sh data/* 2>/dev/null | sort -h
```

### Count files by folder
```bash
find data -type f | awk -F/ '{
  path=""
  for (i=1; i<=NF-1; i++) {
    path = path (i==1 ? $i : "/" $i)
    counts[path]++
  }
}
END {
  for (k in counts) print counts[k], k
}' | sort -nr
```

### Show the most recent files
```bash
find data -type f -printf '%TY-%Tm-%Td %TH:%TM %p\n' 2>/dev/null | sort -r | head -n 50
```

Portable fallback:
```bash
python - <<'PY'
from pathlib import Path
files = sorted(Path("data").rglob("*"), key=lambda p: p.stat().st_mtime if p.is_file() else 0, reverse=True)
for f in files[:50]:
    if f.is_file():
        print(f)
PY
```

### List the latest normalized records
```bash
python - <<'PY'
from pathlib import Path
p = Path("data/normalized/records")
files = sorted([f for f in p.glob("*.json") if f.is_file()], key=lambda x: x.stat().st_mtime, reverse=True)[:10]
for f in files:
    print(f)
PY
```

### List the latest batch summaries
```bash
python - <<'PY'
from pathlib import Path
p = Path("data/normalized/batches")
files = sorted([f for f in p.glob("*.json") if f.is_file()], key=lambda x: x.stat().st_mtime, reverse=True)[:10]
for f in files:
    print(f)
PY
```

### Run a batch generation
```bash
python -m src.normalize.run_synthetic_lr_batch
```

### Run evaluation on a batch summary
```bash
python -m src.evaluate.run_evaluation data/normalized/batches/<batch_summary>.json
```

### Run a small smoke evaluation
```bash
python -m src.evaluate.run_evaluation data/normalized/batches/<batch_summary>.json 6
```

## What to inspect first

If you are trying to understand a run end to end, inspect files in this order:

1. `data/normalized/batches/<batch_summary>.json`
2. `data/normalized/records/<record_id>.json`
3. `data/evaluations/<eval_run>.json`
4. `data/reports/<eval_run>.md`

That sequence shows the full path from generation to saved record to judge evaluation to report.

## What not to edit manually

Avoid manually editing generated JSON artifacts unless you are intentionally fixing a test fixture or debugging a pipeline bug. In particular:
- do not hand-edit `data/normalized/records/*.json` if the files came from a live run,
- do not edit `data/normalized/batches/*.json` unless you are repairing a broken artifact,
- do not edit `data/evaluations/*.json` unless you are creating or updating a tracked example.

## Notes

- `data/normalized/records/` is the canonical store for accepted records.
- `data/review_queue/` contains records that need inspection rather than normalization.
- Evaluation outputs should usually be interpreted together with the corresponding batch summary.
- If you want the latest review artifact, sort files by modification time inside each review subfolder rather than assuming a single newest file across both buckets.
- The repo is intentionally lean, so old or duplicate artifacts should be removed only when they are no longer useful as references.