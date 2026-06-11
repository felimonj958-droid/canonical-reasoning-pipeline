from __future__ import annotations

from src.persist.models import CanonicalRecord


def choose_destination(record: CanonicalRecord) -> tuple[str, str | None]:
    if record.validation.status != "needs_review":
        record.validation.review_reason = None
        return "normalized", None

    errors = set(record.validation.errors or [])

    if {
        "invalid_choice_count",
        "invalid_choice_labels",
    } & errors:
        reason = "malformed_split"
    elif {
        "missing_section",
        "missing_passage",
        "missing_raw_text",
        "missing_normalized_text",
        "missing_stimulus_or_passage",
    } & errors:
        reason = "missing_fields"
    else:
        reason = "ambiguous_classification"

    record.validation.review_reason = reason
    return "review", reason
