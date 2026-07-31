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
    num_candidates: int = 1,
):
    """Run one synthetic LR item through the full canonical lane.

    Backend is resolved from the LLM_BACKEND env var when `client` is None.
    The generation backend and model actually used are recorded on the
    canonical record via `record.generation` (Pydantic `GenerationMeta`).
    """
    client = client or get_llm_client()
    if num_candidates < 1:
        raise ValueError("num_candidates must be >= 1")

    import random

    candidates = []
    candidate_temps = [0.55, 0.75, 0.95]
    candidate_positions = ["A", "B", "C", "D", "E"]
    random.shuffle(candidate_positions)

    for candidate_index in range(num_candidates):

        temp = candidate_temps[candidate_index % len(candidate_temps)]
        position = candidate_positions[candidate_index % len(candidate_positions)]

        raw_output, generation_meta = generate_synthetic_lr(
            flaw_type=flaw_type,
            difficulty=difficulty,
            client=client,
            model=model,
            prompt_version=prompt_version,
            temperature=temp,
            correct_position=position,
        )

        payload = parse_synthetic_lr_output(raw_output)
        validation_result = validate_synthetic_lr_payload(payload)
        quality_result = None
        score = -1
        if validation_result.get("status") == "valid":
            quality_result = run_content_quality_checks(payload)
            score = 0
            if quality_result.status == "pass":
                score += 50
            score += int(quality_result.score * 5)
        candidates.append(
            {
                "candidate_index": candidate_index,
                "raw_output": raw_output,
                "payload": payload,
                "validation_result": validation_result,
                "quality_result": quality_result,
                "generation_meta": generation_meta,
                "score": score,
            }
        )
    candidate_scores = [
        {
            "candidate_index": c["candidate_index"],
            "score": c["score"],
            "validation_status": c["validation_result"].get("status"),
            "quality_status": c["quality_result"].status if c["quality_result"] else None,
            "quality_score": c["quality_result"].score if c["quality_result"] else None,
        }
        for c in candidates
    ]    
    valid_candidates = [
        c for c in candidates
        if c["validation_result"].get("status") == "valid"
    ]
    if not valid_candidates:
        first = candidates[0] if candidates else None
        return {
            "status": "needs_review",
            "stage": "synthetic_structural",
            "errors": first["validation_result"].get("errors", []) if first else ["no_candidates"],
            "payload": first["payload"] if first else {},
            "record": None,
            "content_quality": None,
            "destination": ("review", "synthetic_structural"),
            "saved_path": None,
            "generation_meta": first["generation_meta"] if first else None,
            "candidates": candidates,
            "candidate_scores": candidate_scores,
            "selected_candidate_index": None,
            "selection_reason": {
                "num_candidates": len(candidates),
                "num_valid_candidates": 0,
                "selected_score": None,
            },
        }
    def _candidate_sort_key(candidate: dict):
        q = candidate["quality_result"]
        quality_score = q.score if q is not None else 0
        quality_status_rank = 1 if q is not None and q.status == "pass" else 0
        return (
            candidate["score"],
            quality_status_rank,
            quality_score,
            -candidate["candidate_index"],
        )
    winner = max(valid_candidates, key=_candidate_sort_key)
    payload = winner["payload"]
    generation_meta = winner["generation_meta"]
    quality_result = winner["quality_result"]
    selection_reason = {
        "num_candidates": len(candidates),
        "num_valid_candidates": len(valid_candidates),
        "selected_score": winner["score"],
    }
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

    if quality_result and quality_result.flags:
        for flag in quality_result.flags:
            tagged_flag = f"synthetic_quality:{flag}"
            if tagged_flag not in record.validation.warnings:
                record.validation.warnings.append(tagged_flag)
    if quality_result and quality_result.status == "review":
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
        "candidate_scores": candidate_scores,
        "selection_reason": selection_reason,
        "content_quality": {
            "status": quality_result.status if quality_result else None,
            "score": quality_result.score if quality_result else None,
            "flags": quality_result.flags if quality_result else [],
            "metrics": quality_result.metrics if quality_result else {},
        },
        "candidates": candidates,
        "selected_candidate_index": winner["candidate_index"],
        "destination": destination,
        "saved_path": saved_path,
        "generation_meta": generation_meta,
    }