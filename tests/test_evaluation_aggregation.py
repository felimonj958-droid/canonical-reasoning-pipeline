"""Tests for aggregate_scores — offline, no LLM calls."""
from __future__ import annotations

from src.evaluate.judge_rubric import JudgeScore
from src.evaluate.llm_judge import JudgeResult
from src.evaluate.run_evaluation import (
    _estimate_judge_cost,
    aggregate_scores,
)


def _mk_result(record_id: str, dims: tuple[int, ...], status: str = "scored", flaw_type: str = "causal") -> JudgeResult:
    if status != "scored":
        return JudgeResult(record_id=record_id, status=status, flaw_type=flaw_type)
    score = JudgeScore(
        argument_coherence=dims[0],
        flaw_fidelity=dims[1],
        question_stem_quality=dims[2],
        distractor_plausibility=dims[3],
        correct_answer_precision=dims[4],
        notes="test",
    )
    return JudgeResult(record_id=record_id, status="scored", score=score, flaw_type=flaw_type)


def test_aggregate_empty_list():
    result = aggregate_scores([])
    assert result["items_evaluated"] == 0
    assert result["items_scored"] == 0
    assert result["high_quality_count"] == 0
    assert result["flaw_type_breakdown"] == {}


def test_aggregate_all_high_quality():
    results = [
        _mk_result("r1", (5, 5, 4, 4, 4)),  # 22
        _mk_result("r2", (5, 5, 5, 4, 4)),  # 23
        _mk_result("r3", (4, 4, 4, 4, 4)),  # 20
    ]
    agg = aggregate_scores(results)
    assert agg["items_scored"] == 3
    assert agg["high_quality_count"] == 3
    assert agg["high_quality_rate"] == 1.0
    assert agg["score_total_mean"] == round((22 + 23 + 20) / 3, 2)


def test_aggregate_mixed_quality():
    results = [
        _mk_result("r1", (5, 5, 5, 5, 5)),  # 25 — high
        _mk_result("r2", (3, 3, 3, 3, 3), flaw_type="sampling"),  # 15 — low
        _mk_result("r3", (5, 4, 4, 4, 4)),  # 21 — high
    ]
    agg = aggregate_scores(results)
    assert agg["items_scored"] == 3
    assert agg["high_quality_count"] == 2
    assert agg["high_quality_rate"] == round(2 / 3, 3)


def test_aggregate_mixes_scored_and_errors():
    results = [
        _mk_result("r1", (5, 5, 5, 5, 5)),
        _mk_result("r2", (), status="parse_error"),
        _mk_result("r3", (), status="runtime_error"),
    ]
    agg = aggregate_scores(results)
    assert agg["items_evaluated"] == 3
    assert agg["items_scored"] == 1
    assert agg["items_parse_error"] == 1
    assert agg["items_runtime_error"] == 1
    assert agg["high_quality_count"] == 1


def test_dimension_means_are_computed():
    results = [
        _mk_result("r1", (5, 4, 3, 2, 1)),
        _mk_result("r2", (5, 4, 3, 2, 1)),
        _mk_result("r3", (5, 4, 3, 2, 1)),
    ]
    agg = aggregate_scores(results)
    means = agg["dimension_means"]
    assert means["argument_coherence"] == 5.0
    assert means["flaw_fidelity"] == 4.0
    assert means["question_stem_quality"] == 3.0
    assert means["distractor_plausibility"] == 2.0
    assert means["correct_answer_precision"] == 1.0


def test_flaw_type_breakdown_is_computed():
    results = [
        _mk_result("r1", (5, 5, 5, 5, 5), flaw_type="causal"),
        _mk_result("r2", (3, 3, 3, 3, 3), flaw_type="sampling"),
        _mk_result("r3", (4, 4, 4, 4, 4), flaw_type="causal"),
    ]
    agg = aggregate_scores(results)
    breakdown = agg["flaw_type_breakdown"]
    assert breakdown["causal"]["items_scored"] == 2
    assert breakdown["sampling"]["items_scored"] == 1
    assert breakdown["causal"]["high_quality_count"] == 2


def test_judge_cost_gpt_4o_mini():
    cost = _estimate_judge_cost("gpt-4o-mini", 30000, 10000)
    # 30000 * 0.15 / 1M + 10000 * 0.60 / 1M = 0.0045 + 0.006 = 0.0105
    assert abs(cost - 0.0105) < 1e-6


def test_judge_cost_unknown_model_returns_zero():
    assert _estimate_judge_cost("mystery-model", 1000, 1000) == 0.0
