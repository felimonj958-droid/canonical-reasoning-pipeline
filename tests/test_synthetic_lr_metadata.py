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


def test_synthetic_lr_lane_sets_generation_metadata(monkeypatch):
    payload = {
        "stimulus": (
            "A survey found that towns with more public gardens also report "
            "higher resident satisfaction, so the mayor concludes that adding "
            "gardens will increase satisfaction."
        ),
        "question": (
            "Which one of the following most accurately describes a flaw in the argument?"
        ),
        "answer_choices": [
            {
                "label": "A",
                "text": "It treats a correlation between two things as if it established that one causes the other.",
            },
            {
                "label": "B",
                "text": "It rejects a claim merely because the claim has not been proven.",
            },
            {
                "label": "C",
                "text": "It assumes that what is true of one member of a group is true of all members.",
            },
            {
                "label": "D",
                "text": "It attacks the character of people who disagree instead of addressing their reasons.",
            },
            {
                "label": "E",
                "text": "It relies on a key term in two different senses without noticing the shift.",
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

    result = run_synthetic_lr_lane(
        model="qwen3:8b",
        flaw_type="causal",
        difficulty="medium",
        persist=False,
    )

    record = result["record"]

    assert record is not None

    # Existing assertions: source-side metadata still reflects prompt/model provenance
    assert record.lsat.question_type == "causal"
    assert record.lsat.difficulty == "medium"
    assert record.source.source_uri is not None
    assert "model=qwen3:8b" in record.source.source_uri
    assert "prompt_version=lr_flaw_v1" in record.source.source_uri

    # New assertions: canonical generation metadata is attached to the record
    assert record.generation is not None
    assert record.generation.backend == "fake"
    assert record.generation.model == "qwen3:8b"
    assert record.generation.flaw_type == "causal"
    assert record.generation.difficulty == "medium"
    assert record.generation.prompt_version == "lr_flaw_v1"