from __future__ import annotations

from typing import Optional

from src.persist.models import (
    AnswerChoice,
    CanonicalRecord,
    ContentInfo,
    GenerationMeta,
    LSATInfo,
    SourceInfo,
)


def map_synthetic_lr_to_record(
    payload: dict,
    *,
    source_meta: Optional[dict] = None,
    generation_meta: Optional[GenerationMeta] = None,
) -> CanonicalRecord:
    """Map a parsed synthetic LR payload into a CanonicalRecord.

    - `source_meta` carries source/prompt provenance (file, section,
      difficulty, flaw_type, prompt_version, model_name). It shapes the
      SourceInfo and LSATInfo sections of the record.
    - `generation_meta` is the Pydantic GenerationMeta produced by the
      LLMClient layer (backend, model actually used, token counts, latency)
      and is attached to record.generation.
    """
    source_meta = source_meta or {}

    answer_choices = [
        AnswerChoice(label=choice["label"], text=choice["text"])
        for choice in payload.get("answer_choices", [])
    ]

    raw_output = (payload.get("raw_output") or "").strip()

    normalized_parts = [
        (payload.get("stimulus") or "").strip(),
        (payload.get("question") or "").strip(),
        *[
            f'{choice["label"]}. {choice["text"]}'.strip()
            for choice in payload.get("answer_choices", [])
        ],
    ]
    normalized_text = "\n".join(part for part in normalized_parts if part)

    # Prefer the actual backend/model recorded on generation_meta when
    # composing the fallback source_uri, so it reflects reality rather
    # than a hardcoded backend name.
    backend_name = (
        generation_meta.backend if generation_meta is not None else "ollama"
    )
    default_source_file = f"synthetic://{backend_name}"

    source_uri = source_meta.get("source_uri")
    model_name = source_meta.get("model_name") or (
        generation_meta.model if generation_meta is not None else None
    )
    prompt_version = source_meta.get("prompt_version") or (
        generation_meta.prompt_version if generation_meta is not None else None
    )

    if source_uri is None and (model_name or prompt_version):
        parts = [default_source_file]
        if model_name:
            parts.append(f"model={model_name}")
        if prompt_version:
            parts.append(f"prompt_version={prompt_version}")
        source_uri = "|".join(parts)

    source_kwargs = {
        "modality": "generated_text",
        "source_file": source_meta.get("source_file", default_source_file),
        "source_uri": source_uri,
        "page_ref": None,
        "image_ref": None,
        "capture_device": None,
        "ocr_engine": None,
        "ocr_run_id": None,
    }
    if source_meta.get("created_at") is not None:
        source_kwargs["created_at"] = source_meta["created_at"]

    source = SourceInfo(**source_kwargs)

    lsat = LSATInfo(
        prep_test=source_meta.get("prep_test"),
        section=source_meta.get("section", "logical_reasoning"),
        section_number=source_meta.get("section_number"),
        question_number=source_meta.get("question_number"),
        passage_id=source_meta.get("passage_id"),
        question_type=source_meta.get("question_type")
        or source_meta.get("flaw_type"),
        difficulty=source_meta.get("difficulty"),
    )

    content = ContentInfo(
        passage=None,
        stimulus=payload.get("stimulus"),
        question_stem=payload.get("question"),
        answer_choices=answer_choices,
        correct_answer=payload.get("correct_answer"),
        explanation=payload.get("explanation"),
        raw_text=raw_output,
        normalized_text=normalized_text,
    )

    return CanonicalRecord(
        source=source,
        lsat=lsat,
        content=content,
        generation=generation_meta,
    )