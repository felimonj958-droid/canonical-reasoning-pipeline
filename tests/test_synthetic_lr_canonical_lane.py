from src.normalize.run_synthetic_lr_lane import run_synthetic_lr_lane
from src.persist.models import GenerationMeta


def _fake_generation_meta(**kwargs):
    return GenerationMeta(
        backend="fake",
        model="qwen3:8b",
        flaw_type=kwargs.get("flaw_type", "causal"),
        difficulty=kwargs.get("difficulty", "medium"),
        prompt_version=kwargs.get("prompt_version", "lr_flaw_v1"),
        temperature=0.7,
        max_tokens=1024,
    )


def test_run_synthetic_lr_lane_returns_canonical_record_for_valid_payload(monkeypatch):
    raw_output = """Stimulus: A city council member argues that because traffic decreased after one downtown street was closed, the city should close more streets to reduce traffic overall.

Question: Which one of the following most accurately describes a flaw in the council member's reasoning?

A. It treats a result observed in one case as though it must occur in all similar cases.
B. It rejects a proposal solely because the proposal is unpopular.
C. It confuses a necessary condition with a sufficient condition.
D. It relies on ambiguous language in the phrase "reduce traffic overall."
E. It draws a conclusion that simply restates one of its premises.

Correct Answer: A
"""

    parsed_payload = {
        "stimulus": "A city council member argues that because traffic decreased after one downtown street was closed, the city should close more streets to reduce traffic overall.",
        "question": "Which one of the following most accurately describes a flaw in the council member's reasoning?",
        "answer_choices": [
            {"label": "A", "text": "It treats a result observed in one case as though it must occur in all similar cases."},
            {"label": "B", "text": "It rejects a proposal solely because the proposal is unpopular."},
            {"label": "C", "text": "It confuses a necessary condition with a sufficient condition."},
            {"label": "D", "text": 'It relies on ambiguous language in the phrase "reduce traffic overall."'},
            {"label": "E", "text": "It draws a conclusion that simply restates one of its premises."},
        ],
        "correct_answer": "A",
        "raw_output": raw_output,
    }

    monkeypatch.setattr(
        "src.normalize.run_synthetic_lr_lane.generate_synthetic_lr",
        lambda **kwargs: (raw_output, _fake_generation_meta(**kwargs)),
    )
    monkeypatch.setattr(
        "src.normalize.run_synthetic_lr_lane.parse_synthetic_lr_output",
        lambda text: parsed_payload,
    )

    result = run_synthetic_lr_lane()

    assert result["status"] == "valid"
    assert result["errors"] == []
    assert result["record"] is not None

    record = result["record"]
    assert record.source.modality == "generated_text"
    assert record.source.source_file == "synthetic://fake"
    assert record.lsat.section == "logical_reasoning"
    assert record.lsat.difficulty == "medium"
    assert record.content.stimulus == parsed_payload["stimulus"]
    assert record.content.question_stem == parsed_payload["question"]
    assert len(record.content.answer_choices) == 5
    assert record.content.correct_answer == "A"
    assert record.generation is not None
    assert record.generation.backend == "fake"
    assert record.generation.model == "qwen3:8b"


def test_run_synthetic_lr_lane_returns_review_result_for_invalid_payload(monkeypatch):
    raw_output = """Stimulus: Some argument text.

Question: Which one of the following is flawed?

A. First choice
B. Second choice
C. Third choice

Correct Answer: A
"""

    invalid_payload = {
        "stimulus": "Some argument text.",
        "question": "Which one of the following is flawed?",
        "answer_choices": [
            {"label": "A", "text": "First choice"},
            {"label": "B", "text": "Second choice"},
            {"label": "C", "text": "Third choice"},
        ],
        "correct_answer": "A",
        "raw_output": raw_output,
    }

    monkeypatch.setattr(
        "src.normalize.run_synthetic_lr_lane.generate_synthetic_lr",
        lambda **kwargs: (raw_output, _fake_generation_meta(**kwargs)),
    )
    monkeypatch.setattr(
        "src.normalize.run_synthetic_lr_lane.parse_synthetic_lr_output",
        lambda text: invalid_payload,
    )

    result = run_synthetic_lr_lane()

    assert result["status"] == "needs_review"
    assert result["record"] is None
    assert result["errors"]