from __future__ import annotations

from src.persist.models import CanonicalRecord


def choose_destination(record: CanonicalRecord) -> tuple[str, str | None]:
    if record.validation.status != "needs_review":
        record.validation.review_reason = None
        return "normalized", None

    errors = set(record.validation.errors or [])
    warnings = set(record.validation.warnings or [])
    review_reason = record.validation.review_reason

    synthetic_quality_present = (
        review_reason == "synthetic_low_quality"
        or any(flag.startswith("synthetic_quality:") for flag in errors)
        or any(flag.startswith("synthetic_quality:") for flag in warnings)
    )

    malformed_split_errors = {
        "invalid_choice_count",
        "invalid_choice_labels",
        "missing_correct_answer",
        "invalid_correct_answer_label",
        "correct_answer_not_in_choices",
    }

    missing_field_errors = {
        "missing_content_group",
        "missing_passage",
        "missing_question_stem",
        "missing_raw_text",
        "missing_normalized_text",
        "missing_stimulus_or_passage",
    }

    if synthetic_quality_present:
        reason = "synthetic_low_quality"
    elif malformed_split_errors & errors:
        reason = "malformed_split"
    elif missing_field_errors & errors:
        reason = "missing_fields"
    else:
        reason = review_reason or "ambiguous_classification"

    record.validation.review_reason = reason
    return "review", reason
