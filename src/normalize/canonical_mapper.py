from __future__ import annotations

from src.persist.models import (
    AnswerChoice,
    CanonicalRecord,
    ContentInfo,
    RecordMetadata,
    SourceInfo,
)


def map_to_record(source_manifest, raw_text, normalized_text, segments, ocr=None, image_quality=None):
    answer_choices = [
        AnswerChoice(label=choice["label"], text=choice["text"])
        for choice in segments.get("answer_choices", [])
    ]

    source = SourceInfo(
        modality=source_manifest.modality,
        source_file=source_manifest.source_file,
        source_uri=getattr(source_manifest, "source_uri", None),
        page_ref=getattr(source_manifest, "page_ref", None),
        image_ref=getattr(source_manifest, "image_ref", None),
        capture_device=getattr(source_manifest, "capture_device", None),
        ocr_engine=getattr(source_manifest, "ocr_engine", None),
        ocr_run_id=getattr(source_manifest, "ocr_run_id", None),
        created_at=source_manifest.created_at,
    )

    metadata = RecordMetadata(
        content_group=getattr(source_manifest, "content_group", "unknown") or "unknown",
        source_set=getattr(source_manifest, "source_set", None),
        section_number=getattr(source_manifest, "section_number", None),
        question_number=getattr(source_manifest, "question_number", None),
        passage_id=segments.get("passage_id"),
        item_type=getattr(source_manifest, "item_type", None) or segments.get("item_type"),
        difficulty=getattr(source_manifest, "difficulty", None) or segments.get("difficulty"),
    )

    content = ContentInfo(
        passage=segments.get("passage"),
        stimulus=segments.get("stimulus"),
        question_stem=segments.get("question_stem"),
        answer_choices=answer_choices,
        correct_answer=segments.get("correct_answer"),
        explanation=segments.get("explanation"),
        raw_text=raw_text,
        normalized_text=normalized_text,
    )

    return CanonicalRecord(
        source=source,
        metadata=metadata,
        content=content,
    )
