"""MLflow instrumentation for synthetic generation batches.

Design:
- Thin wrapper around mlflow so batch scripts stay clean.
- Context-manager style: `with MLflowTracker(...) as t: t.log_metric(...)`.
- Lazy import so pytest doesn't drag mlflow into every test run.
- No-op mode via TRACKING_DISABLED=1 for CI/tests.
"""
from __future__ import annotations

import os
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional


def get_git_sha() -> str:
    """Return current git commit SHA (short), or 'unknown' if not a git repo."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


class MLflowTracker:
    """Context-managed MLflow run wrapper.

    Usage:
        with MLflowTracker(experiment="synthetic_lr", run_name="batch_v1") as t:
            t.log_params({"backend": "openai", "n_per_config": 4})
            t.log_metric("accepted", 4)
            t.log_artifact("data/batches/summary.json")
    """

    def __init__(
        self,
        experiment: str,
        run_name: Optional[str] = None,
        tags: Optional[dict[str, str]] = None,
        tracking_uri: Optional[str] = None,
        disabled: Optional[bool] = None,
    ):
        self.experiment = experiment
        self.run_name = run_name
        self.tags = tags or {}
        self.tracking_uri = tracking_uri or os.getenv(
            "MLFLOW_TRACKING_URI", "file:./mlruns"
        )
        self.disabled = (
            disabled
            if disabled is not None
            else os.getenv("TRACKING_DISABLED", "").lower() in ("1", "true", "yes")
        )
        self._mlflow = None
        self._run = None

    def __enter__(self) -> "MLflowTracker":
        if self.disabled:
            return self
        # Lazy import — keeps mlflow out of the fast test path
        import mlflow

        self._mlflow = mlflow
        mlflow.set_tracking_uri(self.tracking_uri)
        mlflow.set_experiment(self.experiment)
        self._run = mlflow.start_run(run_name=self.run_name, tags=self.tags)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._mlflow is None:
            return
        if exc_type is not None:
            self._mlflow.set_tag("status", "failed")
            self._mlflow.set_tag("error_type", exc_type.__name__)
        else:
            self._mlflow.set_tag("status", "success")
        self._mlflow.end_run()

    # ---- Logging API ----

    def log_params(self, params: dict[str, Any]) -> None:
        if self._mlflow is None:
            return
        # mlflow requires str values for params; cast for safety
        self._mlflow.log_params({k: str(v) for k, v in params.items()})

    def log_metric(self, key: str, value: float, step: Optional[int] = None) -> None:
        if self._mlflow is None:
            return
        self._mlflow.log_metric(key, float(value), step=step)

    def log_metrics(self, metrics: dict[str, float], step: Optional[int] = None) -> None:
        if self._mlflow is None:
            return
        self._mlflow.log_metrics(
            {k: float(v) for k, v in metrics.items()}, step=step
        )

    def log_artifact(self, path: str | Path, artifact_path: Optional[str] = None) -> None:
        if self._mlflow is None:
            return
        p = Path(path)
        if not p.exists():
            return
        self._mlflow.log_artifact(str(p), artifact_path=artifact_path)

    def set_tag(self, key: str, value: str) -> None:
        if self._mlflow is None:
            return
        self._mlflow.set_tag(key, value)

    @contextmanager
    def nested_run(self, run_name: str, tags: Optional[dict[str, str]] = None) -> Iterator["MLflowTracker"]:
        """Start a nested run — useful for per-config tracking inside a batch."""
        if self._mlflow is None:
            yield self
            return
        with self._mlflow.start_run(run_name=run_name, nested=True, tags=tags or {}):
            yield self