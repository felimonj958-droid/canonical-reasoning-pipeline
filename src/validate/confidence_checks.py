from __future__ import annotations

from src.persist.models import CanonicalRecord


def validate_record(record: CanonicalRecord) -> CanonicalRecord:
    errors: list[str] = []
    warnings: list[str] = []

    content_group = record.metadata.content_group

    if not content_group or content_group == "unknown":
        errors.append("missing_content_group")

    has_stimulus = bool(record.content.stimulus and record.content.stimulus.strip())
    has_passage = bool(record.content.passage and record.content.passage.strip())
    has_question_stem = bool(record.content.question_stem and record.content.question_stem.strip())
    has_raw_text = bool(record.content.raw_text and record.content.raw_text.strip())
    has_normalized_text = bool(record.content.normalized_text and record.content.normalized_text.strip())

    if not has_raw_text:
        errors.append("missing_raw_text")

    if not has_normalized_text:
        errors.append("missing_normalized_text")

    if content_group == "reading_comprehension":
        if not has_passage:
            errors.append("missing_passage")
    else:
        if not (has_stimulus or has_passage or has_question_stem):
            errors.append("missing_stimulus_or_passage")

    if content_group == "logical_reasoning" and not has_question_stem:
        errors.append("missing_question_stem")

    choices = record.content.answer_choices or []
    labels = [choice.label for choice in choices]

    if choices:
        if len(choices) != 5:
            errors.append("invalid_choice_count")
        if labels != ["A", "B", "C", "D", "E"]:
            errors.append("invalid_choice_labels")

    correct_answer = (record.content.correct_answer or "").strip()
    if not correct_answer:
        errors.append("missing_correct_answer")
    elif correct_answer not in {"A", "B", "C", "D", "E"}:
        errors.append("invalid_correct_answer_label")
    elif labels and correct_answer not in labels:
        errors.append("correct_answer_not_in_choices")

    record.validation.errors = errors
    record.validation.warnings = warnings

    if errors:
        record.validation.status = "needs_review"
    else:
        record.validation.status = "valid"
        record.validation.review_reason = None

    return record
