from pathlib import Path

from src.normalize.run_image_lane import run_image_lane


def test_run_image_lane_routes_multi_question_image_to_review():
    record, out_path, review_path = run_image_lane(
        "tests/fixtures/sample_reasoning_image.jpeg",
        {
            "prep_test": "PT62",
            "section": "logical_reasoning",
            "section_number": 2,
            "question_number": 1,
            "page_ref": "lr2",
            "capture_device": "iPhone",
            "modality": "image",
        },
    )

    assert Path(out_path).exists()
    assert record.lsat.section == "logical_reasoning"
    assert record.validation.status == "needs_review"
    assert review_path is not None
    assert "malformed_split" in str(review_path)
    assert len(record.content.answer_choices) > 5

