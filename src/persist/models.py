from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


Modality = Literal["image", "digital_text", "generated_text"]
ContentGroup = Literal["logical_reasoning", "reading_comprehension", "logic_games", "unknown"]
AnswerLabel = Literal["A", "B", "C", "D", "E"]
ValidationStatus = Literal["valid", "needs_review", "rejected"]
ClassificationStrategy = Literal["straight", "chunked", "hierarchical", "long_context"]


class AnswerChoice(BaseModel):
    label: AnswerLabel
    text: str


class LowConfidenceSpan(BaseModel):
    text: str
    confidence: float
    bbox: List[int] = Field(default_factory=list)


class ImageQuality(BaseModel):
    blur_score: Optional[float] = None
    skew_degrees: Optional[float] = None
    resolution_dpi: Optional[float] = None
    quality_flags: List[str] = Field(default_factory=list)


class OCRInfo(BaseModel):
    mean_confidence: Optional[float] = None
    min_line_confidence: Optional[float] = None
    low_confidence_spans: List[LowConfidenceSpan] = Field(default_factory=list)
    image_quality: ImageQuality = Field(default_factory=ImageQuality)


class ClassificationLabel(BaseModel):
    name: str
    score: float
    label_type: Literal["content_group", "item_type", "topic", "skill", "difficulty"]


class ClassificationChunk(BaseModel):
    chunk_id: str
    start_token: int
    end_token: int
    score: Optional[float] = None


class ClassificationInfo(BaseModel):
    strategy: ClassificationStrategy = "straight"
    labels: List[ClassificationLabel] = Field(default_factory=list)
    ambiguous: bool = False
    token_count: int = 0
    chunks: List[ClassificationChunk] = Field(default_factory=list)


class ValidationInfo(BaseModel):
    status: ValidationStatus = "valid"
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    duplicate_candidates: List[str] = Field(default_factory=list)
    review_reason: Optional[str] = None


class SourceInfo(BaseModel):
    modality: Modality
    source_file: str
    source_uri: Optional[str] = None
    page_ref: Optional[str] = None
    image_ref: Optional[str] = None
    capture_device: Optional[str] = None
    ocr_engine: Optional[str] = None
    ocr_run_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RecordMetadata(BaseModel):
    domain: str = "law_admissions_reasoning"
    content_group: ContentGroup = "unknown"
    source_set: Optional[str] = None
    section_number: Optional[int] = None
    question_number: Optional[int] = None
    passage_id: Optional[str] = None
    item_type: Optional[str] = None
    difficulty: Optional[str] = None


class ContentInfo(BaseModel):
    passage: Optional[str] = None
    stimulus: Optional[str] = None
    question_stem: Optional[str] = None
    answer_choices: List[AnswerChoice] = Field(default_factory=list)
    correct_answer: Optional[AnswerLabel] = None
    explanation: Optional[str] = None
    raw_text: str
    normalized_text: str


class GenerationMeta(BaseModel):
    backend: str
    model: str
    flaw_type: Optional[str] = None
    difficulty: Optional[str] = None
    prompt_version: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    latency_seconds: Optional[float] = None


class CanonicalRecord(BaseModel):
    record_id: str = Field(default_factory=lambda: str(uuid4()))
    schema_version: str = "1.0.0"
    source: SourceInfo
    metadata: RecordMetadata
    content: ContentInfo
    ocr: OCRInfo = Field(default_factory=OCRInfo)
    classification: ClassificationInfo = Field(default_factory=ClassificationInfo)
    validation: ValidationInfo = Field(default_factory=ValidationInfo)
    generation: Optional[GenerationMeta] = None
