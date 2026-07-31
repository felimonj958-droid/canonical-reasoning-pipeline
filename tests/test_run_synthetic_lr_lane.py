from __future__ import annotations

from types import SimpleNamespace

import pytest

import src.normalize.run_synthetic_lr_lane as lane


class DummyQuality:
    def __init__(self, status="pass", score=0.8, flags=None, metrics=None):
        self.status = status
        self.score = score
        self.flags = flags or []
        self.metrics = metrics or {}


class DummyRecord:
    def __init__(self):
        self.validation = SimpleNamespace(
            status="valid",
            errors=[],
            warnings=[],
            review_reason=None,
        )


def _make_payload():
    return {
        "stimulus": "The manager concluded the policy worked because sales increased.",
        "question": "Which one of the following most accurately describes a flaw in the argument?",
        "answer_choices": [
            {"label": "A", "text": "It confuses correlation with causation."},
            {"label": "B", "text": "It fails to consider an alternative explanation."},
            {"label": "C", "text": "It assumes the conclusion follows necessarily."},
            {"label": "D", "text": "It relies on ambiguous terminology."},
            {"label": "E", "text": "It makes a circular argument."},
        ],
        "correct_answer": "A",
    }


@pytest.fixture
def payload():
    return _make_payload()


@pytest.fixture
def record():
    return DummyRecord()


@pytest.fixture
def patch_success_path(monkeypatch, payload, record):
    monkeypatch.setattr(
        lane,
        "generate_synthetic_lr",
        lambda **kwargs: (
            "Stimulus:\n...\nQuestion:\n...\nChoices:\nA. x\nB. y\nC. z\nD. w\nE. v\nCorrect: A",
            SimpleNamespace(backend="openai", model="gpt-4o-mini"),
        ),
    )
    monkeypatch.setattr(lane, "parse_synthetic_lr_output", lambda text: payload)
    monkeypatch.setattr(
        lane,
        "validate_synthetic_lr_payload",
        lambda p: {"status": "valid", "errors": []},
    )
    monkeypatch.setattr(
        lane,
        "run_content_quality_checks",
        lambda p: DummyQuality(),
    )
    monkeypatch.setattr(
        lane,
        "map_synthetic_lr_to_record",
        lambda payload, source_meta, generation_meta: record,
    )
    monkeypatch.setattr(lane, "validate_record", lambda r: r)
    monkeypatch.setattr(lane, "choose_destination", lambda r: ("normalized", None))
    monkeypatch.setattr(lane, "save_record", lambda r, destination: "/tmp/fake.json")


def test_single_candidate_success(patch_success_path):
    out = lane.run_synthetic_lr_lane(num_candidates=1, persist=True)

    assert out["status"] == "valid"
    assert out["stage"] == "synthetic_canonical"
    assert out["selected_candidate_index"] == 0
    assert len(out["candidates"]) == 1
    assert len(out["candidate_scores"]) == 1
    assert out["saved_path"] is not None
    assert out["selection_reason"]["num_candidates"] == 1
    assert out["selection_reason"]["num_valid_candidates"] == 1


def test_multi_candidate_returns_scores(patch_success_path):
    out = lane.run_synthetic_lr_lane(num_candidates=3, persist=False)

    assert out["status"] == "valid"
    assert len(out["candidates"]) == 3
    assert len(out["candidate_scores"]) == 3
    assert out["selected_candidate_index"] in {0, 1, 2}
    assert out["selection_reason"]["num_candidates"] == 3
    assert out["selection_reason"]["num_valid_candidates"] == 3


def test_structural_review_when_all_invalid(monkeypatch, payload):
    monkeypatch.setattr(
        lane,
        "generate_synthetic_lr",
        lambda **kwargs: (
            "bad output",
            SimpleNamespace(backend="openai", model="gpt-4o-mini"),
        ),
    )
    monkeypatch.setattr(lane, "parse_synthetic_lr_output", lambda text: payload)
    monkeypatch.setattr(
        lane,
        "validate_synthetic_lr_payload",
        lambda p: {"status": "needs_review", "errors": ["invalid_choice_count"]},
    )

    out = lane.run_synthetic_lr_lane(num_candidates=2, persist=False)

    assert out["status"] == "needs_review"
    assert out["stage"] == "synthetic_structural"
    assert out["selected_candidate_index"] is None
    assert len(out["candidates"]) == 2
    assert len(out["candidate_scores"]) == 2
    assert out["selection_reason"]["num_valid_candidates"] == 0


def test_invalid_num_candidates_raises():
    with pytest.raises(ValueError):
        lane.run_synthetic_lr_lane(num_candidates=0, persist=False)