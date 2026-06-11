from __future__ import annotations

from pathlib import Path


NORMALIZED_DIR = Path("data/normalized/records")
REVIEW_QUEUE_DIR = Path("data/review_queue")


def save_record(record, destination: str = "normalized", review_reason: str | None = None) -> Path:
    if destination == "review":
        review_reason = review_reason or "missing_fields"
        out_dir = REVIEW_QUEUE_DIR / review_reason
    else:
        out_dir = NORMALIZED_DIR

    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / f"{record.record_id}.json"
    out_path.write_text(record.model_dump_json(indent=2), encoding="utf-8")
    return out_path
