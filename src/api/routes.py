from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.normalize.canonical_mapper import map_to_record
from src.persist.filesystem_store import save_record
from src.validate.confidence_checks import validate_record
from src.validate.review_routing import choose_destination


router = APIRouter(prefix="/records", tags=["records"])


class CreateRecordRequest(BaseModel):
    modality: str = "digital_text"
    source_file: str
    page_ref: Optional[str] = None
    image_ref: Optional[str] = None
    capture_device: Optional[str] = None
    ocr_engine: Optional[str] = None
    content_group: Optional[str] = None
    item_type: Optional[str] = None
    difficulty: Optional[str] = None
    section_number: Optional[int] = None
    question_number: Optional[int] = None
    raw_text: str
    normalized_text: str
    segments: Dict[str, Any] = Field(default_factory=dict)


@router.get("/health")
def records_health():
    return {"status": "ok"}


@router.post("")
def create_record(payload: CreateRecordRequest):
    source_manifest = SimpleNamespace(
        modality=payload.modality,
        source_file=payload.source_file,
        source_uri=None,
        page_ref=payload.page_ref,
        image_ref=payload.image_ref,
        capture_device=payload.capture_device,
        ocr_engine=payload.ocr_engine,
        ocr_run_id=None,
        created_at=datetime.now(timezone.utc),
        content_group=payload.content_group,
        item_type=payload.item_type,
        difficulty=payload.difficulty,
        section_number=payload.section_number,
        question_number=payload.question_number,
    )

    record = map_to_record(
        source_manifest=source_manifest,
        raw_text=payload.raw_text,
        normalized_text=payload.normalized_text,
        segments=payload.segments,
    )

    record = validate_record(record)
    destination, review_reason = choose_destination(record)
    saved_path = save_record(record, destination=destination, review_reason=review_reason)

    return {
        "record_id": record.record_id,
        "status": record.validation.status,
        "review_reason": record.validation.review_reason,
        "saved_path": str(saved_path),
        "record": record.model_dump(),
    }
