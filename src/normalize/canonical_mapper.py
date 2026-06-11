from src.persist.models import (
    AnswerChoice,
    CanonicalRecord,
    ContentInfo,
    LSATInfo,
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
        page_ref=source_manifest.page_ref,
        image_ref=source_manifest.image_ref,
        capture_device=source_manifest.capture_device,
        ocr_engine=source_manifest.ocr_engine,
        created_at=source_manifest.created_at,
    )

    lsat = LSATInfo(
        prep_test=source_manifest.prep_test,
        section=source_manifest.section or "unknown",
        section_number=source_manifest.section_number,
        question_number=source_manifest.question_number,
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
        lsat=lsat,
        content=content,
    )

