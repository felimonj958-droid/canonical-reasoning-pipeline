from __future__ import annotations

from src.persist.models import CanonicalRecord


def validate_record(record: CanonicalRecord) -> CanonicalRecord:
    errors: list[str] = []
    warnings: list[str] = []

    if not record.lsat.section or record.lsat.section == "unknown":
        errors.append("missing_section")

    has_stimulus = bool(record.content.stimulus and record.content.stimulus.strip())
    has_passage = bool(record.content.passage and record.content.passage.strip())
    has_question_stem = bool(record.content.question_stem and record.content.question_stem.strip())
    has_raw_text = bool(record.content.raw_text and record.content.raw_text.strip())
    has_normalized_text = bool(record.content.normalized_text and record.content.normalized_text.strip())

    if not has_raw_text:
        errors.append("missing_raw_text")

    if not has_normalized_text:
        errors.append("missing_normalized_text")

    if record.lsat.section == "reading_comprehension":
        if not has_passage:
            errors.append("missing_passage")
    else:
        if not (has_stimulus or has_passage or has_question_stem):
            errors.append("missing_stimulus_or_passage")

    choices = record.content.answer_choices or []
    if choices:
        labels = [choice.label for choice in choices]
        if len(choices) != 5:
            errors.append("invalid_choice_count")
        if labels != ["A", "B", "C", "D", "E"]:
            errors.append("invalid_choice_labels")

    record.validation.errors = errors
    record.validation.warnings = warnings

    if errors:
        record.validation.status = "needs_review"
    else:
        record.validation.status = "valid"

    return record
