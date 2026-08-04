# Tracking

This package contains the small MLflow wrapper and repository metadata helper used for experiment logging. It keeps batch generation and evaluation code simple by centralizing run setup, metrics logging, artifact logging, and Git SHA capture.

## What this package does

The tracking layer is responsible for:

- starting and ending MLflow runs,
- logging parameters, metrics, tags, and artifacts,
- supporting nested runs when needed,
- exposing the current Git commit hash for reproducibility.

## Files

### `mlflow_tracker.py`
Thin wrapper around MLflow with lazy import behavior.

Main responsibilities:
- configure the MLflow tracking URI and experiment,
- start parent and nested runs,
- log params, metrics, tags, and artifacts,
- keep MLflow optional in fast paths and tests,
- return the active run context cleanly.

Key functions and methods:
- `get_git_sha`
- `__init__`
- `__enter__`
- `__exit__`
- `log_params`
- `log_metric`
- `log_metrics`
- `log_artifact`
- `set_tag`
- `nested_run`

### `__init__.py`
Public tracking exports.

Main responsibilities:
- expose the tracker and Git helper as the package API.

## Dependency flow

This package is used by:

- `src.normalize.run_synthetic_lr_batch`
- `src.evaluate.run_evaluation`

It depends on:

- `mlflow`
- local git metadata access for commit hashing

## What to inspect first

If you are debugging experiment logging, inspect these files in order:

1. `mlflow_tracker.py`
2. `src.normalize.run_synthetic_lr_batch`
3. `src.evaluate.run_evaluation`

## Commands

Run the tracking tests:

```bash
pytest -q tests/test_mlflow_tracker.py
```

Inspect the tracker class and helpers:

```bash
grep -R "class MLflowTracker\|def get_git_sha\|def nested_run" -n src/tracking
```

## Notes

- This package should stay small and dependency-light.
- Keep the logging contract stable because both batch generation and evaluation depend on it.
- When run metadata changes, update the normalize and evaluate READMEs together.
