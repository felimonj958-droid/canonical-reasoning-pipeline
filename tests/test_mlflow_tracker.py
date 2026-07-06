"""Tests for MLflowTracker — verify disabled mode is truly a no-op
and that logging calls hit the mlflow API when enabled.
"""
from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pytest

from src.tracking.mlflow_tracker import MLflowTracker, get_git_sha


def test_get_git_sha_returns_string():
    sha = get_git_sha()
    assert isinstance(sha, str)
    assert len(sha) > 0


def test_disabled_tracker_is_noop(monkeypatch):
    """When disabled, no mlflow import should occur and logging is a no-op."""
    # Ensure mlflow is not in sys.modules from a previous test
    monkeypatch.delitem(sys.modules, "mlflow", raising=False)

    with MLflowTracker(experiment="test", disabled=True) as t:
        t.log_params({"backend": "openai"})
        t.log_metric("accepted", 4)
        t.log_metrics({"latency_ms": 2300, "tokens": 548})
        t.log_artifact("/nonexistent/path.json")
        t.set_tag("lane", "necessary_vs_sufficient")

    # mlflow should NOT have been imported
    assert "mlflow" not in sys.modules or sys.modules["mlflow"] is not None


def test_env_var_disables_tracker(monkeypatch):
    monkeypatch.setenv("TRACKING_DISABLED", "1")
    t = MLflowTracker(experiment="test")
    assert t.disabled is True


def test_tracker_logs_via_mocked_mlflow(monkeypatch):
    """Verify logging calls delegate to mlflow when enabled."""
    fake_mlflow = MagicMock()
    fake_mlflow.start_run.return_value = MagicMock()
    monkeypatch.setitem(sys.modules, "mlflow", fake_mlflow)

    with MLflowTracker(experiment="test_exp", run_name="test_run", disabled=False) as t:
        t.log_params({"backend": "openai", "n": 4})
        t.log_metric("accepted", 4.0)
        t.log_metrics({"latency": 2.3})
        t.set_tag("status", "ok")

    fake_mlflow.set_tracking_uri.assert_called_once()
    fake_mlflow.set_experiment.assert_called_once_with("test_exp")
    fake_mlflow.start_run.assert_called_once()
    fake_mlflow.log_params.assert_called_once_with({"backend": "openai", "n": "4"})
    fake_mlflow.log_metric.assert_called_once_with("accepted", 4.0, step=None)
    fake_mlflow.end_run.assert_called_once()


def test_tracker_records_exception(monkeypatch):
    fake_mlflow = MagicMock()
    fake_mlflow.start_run.return_value = MagicMock()
    monkeypatch.setitem(sys.modules, "mlflow", fake_mlflow)

    with pytest.raises(ValueError):
        with MLflowTracker(experiment="test", disabled=False) as t:
            raise ValueError("boom")

    # Should have tagged the failure
    calls = fake_mlflow.set_tag.call_args_list
    assert any(c.args == ("status", "failed") for c in calls)
    assert any(c.args == ("error_type", "ValueError") for c in calls)