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


def test_synthetic_lr_lane_routes_low_quality_payload_to_review(monkeypatch):
    payload = {
        "stimulus": (
            "As an AI, here is your LSAT question. A teacher concludes that online "
            "quizzes improve learning because students who took them scored better "
            "on the final exam."
        ),
        "question": "What do you think about this argument?",
        "answer_choices": [
            {
                "label": "A",
                "text": "The students who took online quizzes also attended extra tutoring sessions.",
            },
            {
                "label": "B",
                "text": "Some students dislike final exams.",
            },
            {
                "label": "C",
                "text": "Tutoring can be expensive.",
            },
            {
                "label": "D",
                "text": "Many teachers use online tools.",
            },
            {
                "label": "E",
                "text": "Some students prefer shorter quizzes.",
            },
        ],
        "correct_answer": "A",
    }

    monkeypatch.setattr(
        "src.normalize.run_synthetic_lr_lane.generate_synthetic_lr",
        lambda **kwargs: ("mock raw output", _fake_generation_meta(**kwargs)),
    )
    monkeypatch.setattr(
        "src.normalize.run_synthetic_lr_lane.parse_synthetic_lr_output",
        lambda raw: payload,
    )

    result = run_synthetic_lr_lane(persist=False)

    assert result["status"] == "needs_review"
    assert result["content_quality"]["status"] == "review"
    assert "synthetic_quality:meta_language_detected" in result["errors"]