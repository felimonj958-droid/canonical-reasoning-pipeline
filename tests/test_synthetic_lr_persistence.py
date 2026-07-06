from pathlib import Path

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


def test_synthetic_lr_lane_persists_valid_record(tmp_path, monkeypatch):
    raw_output = """Stimulus: A simple argument.

Question: Which one of the following is most strongly supported?

A. First
B. Second
C. Third
D. Fourth
E. Fifth

Correct Answer: C
"""

    parsed_payload = {
        "stimulus": "A simple argument.",
        "question": "Which one of the following is most strongly supported?",
        "answer_choices": [
            {"label": "A", "text": "First"},
            {"label": "B", "text": "Second"},
            {"label": "C", "text": "Third"},
            {"label": "D", "text": "Fourth"},
            {"label": "E", "text": "Fifth"},
        ],
        "correct_answer": "C",
        "raw_output": raw_output,
    }

    monkeypatch.setattr(
        "src.normalize.run_synthetic_lr_lane.generate_synthetic_lr",
        lambda **kwargs: (raw_output, _fake_generation_meta(**kwargs)),
    )
    monkeypatch.setattr(
        "src.normalize.run_synthetic_lr_lane.parse_synthetic_lr_output",
        lambda text: parsed_payload,
    )

    # Redirect data root so we don't write into the real repo data dir
    monkeypatch.setattr(
        "src.persist.filesystem_store.OUTPUT_ROOT",
        tmp_path,
        raising=False,
    )
    monkeypatch.setattr(
        "src.persist.filesystem_store.REVIEW_ROOT",
        tmp_path / "review_queue",
        raising=False,
    )

    result = run_synthetic_lr_lane(persist=True)

    assert result["status"] == "valid"
    assert result["saved_path"] is not None

    saved_path = Path(result["saved_path"])
    assert saved_path.exists()
    assert saved_path.read_text(encoding="utf-8")