from src.generate.synthetic_lr import parse_synthetic_lr_output


def test_parse_synthetic_lr_output_happy_path():
    sample = """Stimulus:
A recent study found that people who drink coffee are more likely to have heart disease. Therefore, drinking coffee causes heart disease.

Question:
Which answer choice best describes the flaw in the reasoning?

Choices:
A. The study fails to account for confounding variables like stress levels.
B. The study's sample size is too small to draw valid conclusions.
C. The causality could be reversed, with heart disease leading to increased coffee consumption.
D. The study's methodology is flawed because it relies on self-reported data.
E. The correlation observed does not necessarily imply a direct causal relationship.

Correct: E
"""

    parsed = parse_synthetic_lr_output(sample)

    assert parsed["stimulus"].startswith("A recent study found")
    assert parsed["question"] == "Which answer choice best describes the flaw in the reasoning?"
    assert len(parsed["answer_choices"]) == 5
    assert {c["label"] for c in parsed["answer_choices"]} == {"A", "B", "C", "D", "E"}
    assert parsed["correct_answer"] == "E"
