import pytest

from src.generate.synthetic_lr import generate_synthetic_lr, parse_synthetic_lr_output


pytestmark = pytest.mark.integration


def test_generate_and_parse_synthetic_lr_live():
    raw = generate_synthetic_lr(
        model="gpt-4o-mini",
        flaw_type="causal",
        difficulty="medium",
    )

    parsed = parse_synthetic_lr_output(raw)

    assert parsed["stimulus"] != ""
    assert parsed["question"] != ""
    assert len(parsed["answer_choices"]) == 5
    assert {c["label"] for c in parsed["answer_choices"]} == {"A", "B", "C", "D", "E"}
    assert parsed["correct_answer"] in {"A", "B", "C", "D", "E"}
