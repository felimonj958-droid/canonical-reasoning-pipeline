"""Tests for the LLM judge — mocks the client to keep tests offline and deterministic."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from src.evaluate.judge_rubric import JudgeScore, build_judge_prompt
from src.evaluate.llm_judge import _extract_json_block, judge_record


def _mock_record() -> dict:
    return {
        "record_id": "test-abc-123",
        "stimulus": "All ravens observed have been black. Therefore, all ravens are black.",
        "question": "Which of the following most accurately identifies the flaw in the reasoning?",
        "answer_choices": [
            {"label": "A", "text": "It generalizes from a limited sample."},
            {"label": "B", "text": "It assumes what it seeks to prove."},
            {"label": "C", "text": "It confuses necessary with sufficient conditions."},
            {"label": "D", "text": "It attacks the arguer rather than the argument."},
            {"label": "E", "text": "It ignores relevant counterexamples."},
        ],
        "correct_answer": "A",
        "generation": {"flaw_type": "hasty_generalization", "difficulty": "easy"},
    }


def test_build_judge_prompt_uses_generation_fields():
    prompt = build_judge_prompt(_mock_record())
    assert "hasty_generalization" in prompt
    assert "difficulty: easy" in prompt.lower()
    assert "All ravens" in prompt
    assert "A. It generalizes" in prompt


def test_build_judge_prompt_handles_flat_fields():
    record = {
        "flaw_type": "causal",
        "difficulty": "medium",
        "stimulus": "s",
        "question": "q",
        "answer_choices": [{"label": "A", "text": "x"}],
        "correct_answer": "A",
    }
    prompt = build_judge_prompt(record)
    assert "causal" in prompt
    assert "medium" in prompt


def test_extract_json_block_from_fenced_output():
    fenced = '```json\n{"argument_coherence": 5, "notes": "good"}\n```'
    result = _extract_json_block(fenced)
    parsed = json.loads(result)
    assert parsed["argument_coherence"] == 5


def test_extract_json_block_with_prose_prefix():
    output = 'Here is the score:\n{"argument_coherence": 4}\nHope this helps.'
    result = _extract_json_block(output)
    parsed = json.loads(result)
    assert parsed["argument_coherence"] == 4


def test_extract_json_block_nested_braces():
    output = '{"a": {"b": 1}, "c": 2}'
    result = _extract_json_block(output)
    parsed = json.loads(result)
    assert parsed["c"] == 2


def test_judge_score_total_and_high_quality():
    score = JudgeScore(
        argument_coherence=5,
        flaw_fidelity=5,
        question_stem_quality=4,
        distractor_plausibility=4,
        correct_answer_precision=4,
        notes="strong item",
    )
    assert score.total == 22
    assert score.is_high_quality is True

    weak = JudgeScore(
        argument_coherence=3,
        flaw_fidelity=3,
        question_stem_quality=3,
        distractor_plausibility=3,
        correct_answer_precision=3,
        notes="mid",
    )
    assert weak.total == 15
    assert weak.is_high_quality is False


def test_judge_score_rejects_out_of_range():
    with pytest.raises(Exception):
        JudgeScore(
            argument_coherence=6,
            flaw_fidelity=5,
            question_stem_quality=5,
            distractor_plausibility=5,
            correct_answer_precision=5,
        )


def test_judge_record_happy_path_with_mocked_client():
    fake_client = MagicMock()
    fake_client.backend_name = "openai"
    fake_client.model = "gpt-4o-mini"

    fake_response = MagicMock()
    fake_response.text = json.dumps(
        {
            "argument_coherence": 5,
            "flaw_fidelity": 5,
            "question_stem_quality": 4,
            "distractor_plausibility": 4,
            "correct_answer_precision": 4,
            "notes": "well-formed item",
        }
    )
    fake_response.prompt_tokens = 300
    fake_response.completion_tokens = 60
    fake_response.model = "gpt-4o-mini-2024-07-18"
    fake_client.generate.return_value = fake_response

    result = judge_record(_mock_record(), client=fake_client)

    assert result.status == "scored"
    assert result.score.total == 22
    assert result.prompt_tokens == 300
    assert result.completion_tokens == 60
    assert result.judge_model == "gpt-4o-mini-2024-07-18"


def test_judge_record_parse_error_when_bad_json():
    fake_client = MagicMock()
    fake_client.backend_name = "openai"
    fake_response = MagicMock()
    fake_response.text = "Sorry, I can't score this."
    fake_response.prompt_tokens = 100
    fake_response.completion_tokens = 20
    fake_response.model = "gpt-4o-mini"
    fake_client.generate.return_value = fake_response

    result = judge_record(_mock_record(), client=fake_client)
    assert result.status == "parse_error"
    assert result.score is None
    assert "parse_failed" in result.error


def test_judge_record_runtime_error_when_client_raises():
    fake_client = MagicMock()
    fake_client.backend_name = "openai"
    fake_client.generate.side_effect = RuntimeError("api down")

    result = judge_record(_mock_record(), client=fake_client)
    assert result.status == "runtime_error"
    assert result.score is None
    assert "api down" in result.error