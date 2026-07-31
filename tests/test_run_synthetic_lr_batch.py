from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import src.normalize.run_synthetic_lr_batch as batch


class DummyTracker:
    def __init__(self):
        self.params = {}
        self.metrics = {}
        self.tags = {}
        self.artifacts = []
        self.nested_runs = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def log_params(self, params):
        self.params.update(params)

    def log_metrics(self, metrics):
        self.metrics.update(metrics)

    def log_artifact(self, path):
        self.artifacts.append(path)

    def set_tag(self, key, value):
        self.tags[key] = value

    def nested_run(self, run_name, tags=None):
        self.nested_runs.append((run_name, tags or {}))
        return self


class DummyClient:
    backend_name = "openai"
    model = "gpt-4o-mini"


def _fake_lane_out(status="valid", destination=("normalized", None)):
    return {
        "status": status,
        "destination": destination,
        "content_quality": {"status": "pass", "flags": []},
        "saved_path": "/tmp/fake.json",
        "error": None,
        "generation_meta": SimpleNamespace(
            backend="openai",
            model="gpt-4o-mini",
            prompt_tokens=10,
            completion_tokens=20,
            latency_seconds=0.5,
        ),
        "selected_candidate_index": 0,
        "selection_reason": {
            "num_candidates": 3,
            "num_valid_candidates": 3,
            "selected_score": 90,
        },
        "candidate_scores": [
            {
                "candidate_index": 0,
                "score": 90,
                "validation_status": "valid",
                "quality_status": "pass",
                "quality_score": 0.8,
            }
        ],
    }


def test_batch_threads_num_candidates(monkeypatch):
    tracker = DummyTracker()
    lane_calls = []

    monkeypatch.setattr(batch, "get_llm_client", lambda: DummyClient())
    monkeypatch.setattr(batch, "get_git_sha", lambda: "abc123")
    monkeypatch.setattr(batch, "MLflowTracker", lambda **kwargs: tracker)
    monkeypatch.setattr(
        batch,
        "run_synthetic_lr_lane",
        lambda **kwargs: lane_calls.append(kwargs) or _fake_lane_out(),
    )

    out = batch.run_synthetic_lr_batch(
        n_per_config=1,
        persist=False,
        track=False,
        num_candidates=3,
    )

    assert lane_calls
    assert all(call["num_candidates"] == 3 for call in lane_calls)
    assert out["summary"]["num_candidates"] == 3
    assert out["summary"]["total_items"] == 4
    assert len(out["results"]) == 4


def test_batch_results_include_selection_metadata(monkeypatch):
    tracker = DummyTracker()

    monkeypatch.setattr(batch, "get_llm_client", lambda: DummyClient())
    monkeypatch.setattr(batch, "get_git_sha", lambda: "abc123")
    monkeypatch.setattr(batch, "MLflowTracker", lambda **kwargs: tracker)
    monkeypatch.setattr(batch, "run_synthetic_lr_lane", lambda **kwargs: _fake_lane_out())

    out = batch.run_synthetic_lr_batch(
        n_per_config=1,
        persist=False,
        track=False,
        num_candidates=2,
    )

    assert "selected_candidate_index" in out["results"][0]
    assert "selection_reason" in out["results"][0]
    assert "candidate_scores" in out["results"][0]


def test_batch_summary_has_generation_metrics(monkeypatch):
    tracker = DummyTracker()

    monkeypatch.setattr(batch, "get_llm_client", lambda: DummyClient())
    monkeypatch.setattr(batch, "get_git_sha", lambda: "abc123")
    monkeypatch.setattr(batch, "MLflowTracker", lambda **kwargs: tracker)
    monkeypatch.setattr(batch, "run_synthetic_lr_lane", lambda **kwargs: _fake_lane_out())

    out = batch.run_synthetic_lr_batch(
        n_per_config=1,
        persist=False,
        track=False,
        num_candidates=1,
    )

    assert "generation_metrics" in out["summary"]
    assert out["summary"]["generation_metrics"]["items_with_meta"] == 4