from src.normalize.synthetic_mapper import map_synthetic_lr_to_record
from src.persist.models import ValidationInfo
from src.validate.review_routing import choose_destination


def test_choose_destination_routes_synthetic_low_quality_to_dedicated_bucket():
    payload = {
        "stimulus": "A mayor argues that because two things occurred together, one caused the other.",
        "question": "Which one of the following most accurately describes a flaw in the argument?",
        "answer_choices": [
            {"label": "A", "text": "It treats correlation as causation."},
            {"label": "B", "text": "It attacks a person instead of the argument."},
            {"label": "C", "text": "It confuses a whole with a part."},
            {"label": "D", "text": "It relies on a term used ambiguously."},
            {"label": "E", "text": "It mistakes absence of proof for proof of absence."},
        ],
        "correct_answer": "A",
    }

    record = map_synthetic_lr_to_record(payload)
    record.validation = ValidationInfo(
        status="needs_review",
        errors=["synthetic_quality:meta_language_detected"],
        warnings=[],
        review_reason="synthetic_low_quality",
    )

    destination = choose_destination(record)

    assert destination == ("review", "synthetic_low_quality")
    assert record.validation.review_reason == "synthetic_low_quality"
