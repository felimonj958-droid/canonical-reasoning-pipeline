from pathlib import Path

from src.normalize.run_text_lane import run_text_lane


def test_run_text_lane_sample():
    text_path = "data/raw_text/sample.txt"
    metadata = {
        "section": "logical_reasoning",
        "prep_test": "DEMO",
        "modality": "generated_text",
    }

    record, out_path, review_path = run_text_lane(text_path, metadata)

    assert Path(out_path).exists()
    assert review_path is None
    assert record.lsat.section == "logical_reasoning"
    assert len(record.content.answer_choices) == 5

    labels = {c.label for c in record.content.answer_choices}
    assert labels == {"A", "B", "C", "D", "E"}
