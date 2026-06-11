from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field


Modality = Literal["image", "digital_text", "generated_text"]


class IngestionManifest(BaseModel):
    """
    Small, deterministic record describing one ingestion unit, before OCR/cleaning.
    Shared by image_loader and text_loader so downstream code can ignore origin details.
    """

    modality: Modality
    source_file: str  # repo-relative path such as "data/raw_text/sample.txt"
    prep_test: Optional[str] = None
    section: Optional[str] = None
    section_number: Optional[int] = None
    question_number: Optional[int] = None
    page_ref: Optional[str] = None
    image_ref: Optional[str] = None
    capture_device: Optional[str] = None
    ocr_engine: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_path(
        cls,
        path: Path,
        *,
        modality: Modality,
        prep_test: Optional[str] = None,
        section: Optional[str] = None,
        section_number: Optional[int] = None,
        question_number: Optional[int] = None,
        page_ref: Optional[str] = None,
        capture_device: Optional[str] = None,
        ocr_engine: Optional[str] = None,
    ) -> "IngestionManifest":
        return cls(
            modality=modality,
            source_file=str(path),
            prep_test=prep_test,
            section=section,
            section_number=section_number,
            question_number=question_number,
            page_ref=page_ref,
            capture_device=capture_device,
            ocr_engine=ocr_engine,
        )

