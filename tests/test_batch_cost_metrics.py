"""Tests for batch-level generation metric aggregation and cost estimation."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.normalize.run_synthetic_lr_batch import (
    _aggregate_generation_metrics,
    _estimate_cost_usd,
)


@dataclass
class FakeGenMeta:
    backend: str
    model: str
    prompt_tokens: int | None
    completion_tokens: int | None
    latency_seconds: float | None


def test_estimate_cost_known_model():
    cost = _estimate_cost_usd("gpt-4o-mini", prompt_tokens=1_000_000, completion_tokens=1_000_000)
    assert cost == pytest.approx(0.75)


def test_estimate_cost_realistic_values():
    cost = _estimate_cost_usd("gpt-4o-mini", prompt_tokens=392, completion_tokens=156)
    assert cost == pytest.approx(0.000152, abs=1e-6)


def test_estimate_cost_unknown_model_returns_zero():
    assert _estimate_cost_usd("unknown-model-xyz", 1000, 1000) == 0.0


def test_estimate_cost_local_model_returns_zero():
    assert _estimate_cost_usd("qwen3:8b", 1000, 1000) == 0.0


def test_aggregate_empty_list():
    result = _aggregate_generation_metrics([])
    assert result["prompt_tokens_total"] == 0
    assert result["tokens_total"] == 0
    assert result["estimated_cost_usd"] == 0.0
    assert result["items_with_meta"] == 0


def test_aggregate_multiple_records():
    meta_list = [
        FakeGenMeta("openai", "gpt-4o-mini", 400, 150, 2.3),
        FakeGenMeta("openai", "gpt-4o-mini", 380, 160, 2.1),
        FakeGenMeta("openai", "gpt-4o-mini", 410, 145, 2.5),
    ]
    result = _aggregate_generation_metrics(meta_list)

    assert result["prompt_tokens_total"] == 1190
    assert result["completion_tokens_total"] == 455
    assert result["tokens_total"] == 1645
    assert result["items_with_meta"] == 3
    assert result["latency_ms_avg"] == pytest.approx(2300.0, abs=0.01)
    assert result["estimated_cost_usd"] > 0


def test_aggregate_handles_missing_tokens():
    meta_list = [
        FakeGenMeta("openai", "gpt-4o-mini", None, None, 45.0),
        FakeGenMeta("openai", "gpt-4o-mini", 400, 150, 2.3),
    ]
    result = _aggregate_generation_metrics(meta_list)
    assert result["prompt_tokens_total"] == 400
    assert result["completion_tokens_total"] == 150
    assert result["items_with_meta"] == 2


def test_aggregate_handles_missing_latency():
    meta_list = [
        FakeGenMeta("openai", "gpt-4o-mini", 400, 150, None),
    ]
    result = _aggregate_generation_metrics(meta_list)
    assert result["latency_ms_avg"] == 0.0
    assert result["items_with_meta"] == 1


def test_aggregate_single_item_percentiles():
    meta_list = [
        FakeGenMeta("openai", "gpt-4o-mini", 400, 150, 2.3),
    ]
    result = _aggregate_generation_metrics(meta_list)
    assert result["latency_ms_p50"] == 2300.0
    assert result["latency_ms_p95"] == 2300.0
