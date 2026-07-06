from __future__ import annotations

from src.generate.synthetic_lr import generate_synthetic_lr, parse_synthetic_lr_output
from src.generate.validation import validate_synthetic_lr_payload
from src.generate.content_quality_checks import run_content_quality_checks
from src.llm_client import LLMClient, get_llm_client
from src.normalize.synthetic_mapper import map_synthetic_lr_to_record
from src.persist.filesystem_store import save_record
from src.validate.confidence_checks import validate_record
from src.validate.review_routing import choose_destination


def run_synthetic_lr_lane(
    *,
    flaw_type: str = "causal",
    difficulty: str = "medium",
    client: LLMClient | None = None,
    model: str | None = None,          # legacy hint; forwarded to the client
    prompt_version: str = "lr_flaw_v1",
    persist: bool = False,
):
    """Run one synthetic LR item through the full canonical lane.

    Backend is resolved from the LLM_BACKEND env var when `client` is None.
    The generation backend and model actually used are recorded on the
    canonical record via `record.generation` (Pydantic `GenerationMeta`).
    """
    client = client or get_llm_client()

    raw_output, generation_meta = generate_synthetic_lr(
        flaw_type=flaw_type,
        difficulty=difficulty,
        client=client,
        model=model,
        prompt_version=prompt_version,
    )

    payload = parse_synthetic_lr_output(raw_output)
    validation_result = validate_synthetic_lr_payload(payload)
    errors = validation_result.get("errors", [])

    if validation_result.get("status") != "valid":
        return {
            "status": "needs_review",
            "stage": "synthetic_structural",
            "errors": errors,
            "payload": payload,
            "record": None,
            "content_quality": None,
            "destination": ("review", "synthetic_structural"),
            "saved_path": None,
            "generation_meta": generation_meta,
        }

    quality_result = run_content_quality_checks(payload)

    source_meta = {
        "source_file": f"synthetic://{generation_meta.backend}",
        "source_uri": None,
        "section": "logical_reasoning",
        "difficulty": difficulty,
        "flaw_type": flaw_type,
        "prompt_version": prompt_version,
        "model_name": generation_meta.model,
    }

    record = map_synthetic_lr_to_record(
        payload,
        source_meta=source_meta,
        generation_meta=generation_meta,
    )

    record = validate_record(record)

    if quality_result.flags:
        for flag in quality_result.flags:
            tagged_flag = f"synthetic_quality:{flag}"
            if tagged_flag not in record.validation.warnings:
                record.validation.warnings.append(tagged_flag)

    if quality_result.status == "review":
        record.validation.status = "needs_review"
        record.validation.review_reason = "synthetic_low_quality"
        for flag in quality_result.flags:
            tagged_flag = f"synthetic_quality:{flag}"
            if tagged_flag not in record.validation.errors:
                record.validation.errors.append(tagged_flag)

    destination = choose_destination(record)

    saved_path = None
    if persist:
        saved_path = save_record(record, destination)

    return {
        "status": record.validation.status,
        "stage": "synthetic_canonical",
        "errors": record.validation.errors,
        "payload": payload,
        "record": record,
        "content_quality": {
            "status": quality_result.status,
            "score": quality_result.score,
            "flags": quality_result.flags,
            "metrics": quality_result.metrics,
        },
        "destination": destination,
        "saved_path": saved_path,
        "generation_meta": generation_meta,
    }