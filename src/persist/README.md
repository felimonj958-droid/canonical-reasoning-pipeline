# Persistence Layer

This package defines the canonical record models and the filesystem persistence logic used by the active pipeline. It is the source of truth for record structure and for where records are written on disk.

## What this package does

The persistence layer has two jobs:

- define the canonical data model,
- store records in the correct on-disk destination.

It is shared by the synthetic generation pipeline and the API service, so its shape matters to both.

## Files

### `models.py`
Canonical Pydantic models and supporting data structures.

Main responsibilities:
- represent canonical records,
- represent generation metadata,
- represent validation and routing-related state,
- keep the schema stable across generation, API, and evaluation.

Use this file when you need to understand the record schema or the fields that must survive the pipeline.

### `filesystem_store.py`
Filesystem persistence for normalized records and review-queue records.

Main responsibilities:
- write accepted records to normalized storage,
- write rejected or malformed records to the review queue,
- preserve review reasons when present,
- return the saved path for downstream summary tracking.

Key function:
- `save_record`

## Dependency flow

This package is used by:

- `src.normalize.run_synthetic_lr_lane`
- `src.normalize.synthetic_mapper`
- `src.api.routes`
- `src.validate`
- `src.evaluate` indirectly through loaded batch artifacts

It depends on:

- standard filesystem paths under `data/`
- the canonical record models in `models.py`

## What to inspect first

If you are debugging persistence, inspect these files in order:

1. `models.py`
2. `filesystem_store.py`
3. `src.normalize.synthetic_mapper`
4. `src.normalize.run_synthetic_lr_lane`
5. `src.api.routes`

## Commands

Run persistence-related tests:

```bash
pytest -q tests/test_synthetic_lr_persistence.py tests/test_api_records.py
```

Inspect the filesystem save function:

```bash
grep -R "def save_record" -n src/persist
```

Inspect model definitions:

```bash
grep -R "class .*Canonical\|class .*Record\|class .*Meta" -n src/persist
```

## Notes

- This package is one of the most important parts of the repo because it defines both the schema and the durable write path.
- If the schema changes, update this README together with the normalize and validate docs.
- Keep the storage layer simple and deterministic; avoid embedding higher-level orchestration here.
