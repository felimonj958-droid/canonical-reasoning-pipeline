from pathlib import Path

from src.normalize.run_text_lane import run_text_lane
from src.validate.confidence_checks import validate_record
from src.validate.review_routing import choose_destination
from src.persist.filesystem_store import save_record


def test_validation_passes_for_good_sample():
    record, out_path, review_path = run_text_lane(
        "data/raw_text/sample.txt",
        {
            "section": "logical_reasoning",
            "prep_test": "DEMO",
            "modality": "generated_text",
        },
    )

    assert Path(out_path).exists()
    assert record.validation.status == "valid"
    assert record.validation.errors == []
    assert review_path is None


def test_validation_routes_broken_record_to_review():
    record, out_path, review_path = run_text_lane(
        "data/raw_text/sample.txt",
        {
            "section": "logical_reasoning",
            "prep_test": "DEMO",
            "modality": "generated_text",
        },
    )

    record.content.answer_choices = record.content.answer_choices[:3]
    record = validate_record(record)
    destination, review_reason = choose_destination(record)
    routed_path = save_record(record, destination=destination, review_reason=review_reason)

    assert record.validation.status == "needs_review"
    assert "invalid_choice_count" in record.validation.errors
    assert "invalid_choice_labels" in record.validation.errors
    assert destination == "review"
    assert review_reason == "malformed_split"
    assert routed_path is not None
    assert Path(routed_path).exists()
    assert "malformed_split" in str(routed_path)
