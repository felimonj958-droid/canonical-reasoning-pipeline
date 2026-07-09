from __future__ import annotations

import os
from fastapi.testclient import TestClient

from src.api.main import app
from src.persist import filesystem_store


client = TestClient(app)

AUTH_HEADERS = {"Authorization": f"Bearer {os.environ['API_TOKEN']}"}


def test_ingest_ocr_text_valid_record(monkeypatch, tmp_path):
    normalized_dir = tmp_path / "normalized" / "records"
    review_dir = tmp_path / "review_queue"

    monkeypatch.setattr(filesystem_store, "NORMALIZED_DIR", normalized_dir)
    monkeypatch.setattr(filesystem_store, "REVIEW_QUEUE_DIR", review_dir)

    payload = {
        "modality": "digital_text",
        "source_file": "data/raw_text/sample_lr.txt",
        "prep_test": "PT62",
        "section": "logical_reasoning",
        "section_number": 2,
        "question_number": 14,
        "raw_text": (
            "A city council member argues that traffic will improve if parking fees are raised. "
            "Which one of the following is most strongly supported? "
            "A. Choice A B. Choice B C. Choice C D. Choice D E. Choice E"
        ),
        "normalized_text": (
            "A city council member argues that traffic will improve if parking fees are raised. "
            "Which one of the following is most strongly supported? "
            "A. Choice A B. Choice B C. Choice C D. Choice D E. Choice E"
        ),
        "segments": {
            "stimulus": "A city council member argues that traffic will improve if parking fees are raised.",
            "question_stem": "Which one of the following is most strongly supported?",
            "answer_choices": [
                {"label": "A", "text": "Choice A"},
                {"label": "B", "text": "Choice B"},
                {"label": "C", "text": "Choice C"},
                {"label": "D", "text": "Choice D"},
                {"label": "E", "text": "Choice E"},
            ],
        },
    }

    response = client.post("/ingest/ocr-text", json=payload, headers=AUTH_HEADERS)

    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "valid"
    assert body["review_reason"] is None
    assert "data/normalized/records" not in body["saved_path"]

    saved_path = normalized_dir / f"{body['record_id']}.json"
    assert saved_path.exists()

    record = body["record"]
    assert record["lsat"]["section"] == "logical_reasoning"
    assert record["validation"]["status"] == "valid"
    assert len(record["content"]["answer_choices"]) == 5


def test_ingest_ocr_text_malformed_record_routes_to_review(monkeypatch, tmp_path):
    normalized_dir = tmp_path / "normalized" / "records"
    review_dir = tmp_path / "review_queue"

    monkeypatch.setattr(filesystem_store, "NORMALIZED_DIR", normalized_dir)
    monkeypatch.setattr(filesystem_store, "REVIEW_QUEUE_DIR", review_dir)

    payload = {
        "modality": "digital_text",
        "source_file": "data/raw_text/sample_lr_bad.txt",
        "prep_test": "PT62",
        "section": "logical_reasoning",
        "section_number": 2,
        "question_number": 15,
        "raw_text": (
            "An editorial claims that public transit use will increase if fares are lowered. "
            "Which one of the following is most strongly supported? "
            "A. Choice A B. Choice B C. Choice C"
        ),
        "normalized_text": (
            "An editorial claims that public transit use will increase if fares are lowered. "
            "Which one of the following is most strongly supported? "
            "A. Choice A B. Choice B C. Choice C"
        ),
        "segments": {
            "stimulus": "An editorial claims that public transit use will increase if fares are lowered.",
            "question_stem": "Which one of the following is most strongly supported?",
            "answer_choices": [
                {"label": "A", "text": "Choice A"},
                {"label": "B", "text": "Choice B"},
                {"label": "C", "text": "Choice C"},
            ],
        },
    }

    response = client.post(
        "/ingest/ocr-text",
        json=payload,
        headers={"Authorization": f"Bearer {os.environ['API_TOKEN']}"},
    )

    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "needs_review"
    assert body["review_reason"] == "malformed_split"

    saved_path = review_dir / "malformed_split" / f"{body['record_id']}.json"
    assert saved_path.exists()

    record = body["record"]
    assert record["validation"]["status"] == "needs_review"
    assert "invalid_choice_count" in record["validation"]["errors"]
    assert "invalid_choice_labels" in record["validation"]["errors"]