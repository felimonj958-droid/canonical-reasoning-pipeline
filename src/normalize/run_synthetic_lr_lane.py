from __future__ import annotations

import random

from src.generate.synthetic_lr import generate_synthetic_lr, parse_synthetic_lr_output
from src.generate.validation import validate_synthetic_lr_payload
from src.generate.content_quality_checks import run_content_quality_checks
from src.llm_client import LLMClient, get_llm_client
from src.normalize.synthetic_mapper import map_synthetic_lr_to_record
from src.persist.filesystem_store import save_record
from src.validate.confidence_checks import validate_record
from src.validate.review_routing import choose_destination
from typing import Any


Candidate = dict[str, Any]



def _build_candidate(
    *,
    candidate_index: int,
    flaw_type: str,
    difficulty: str,
    client: LLMClient,
    model: str | None,
    prompt_version: str,
    temperature: float,
    correct_position: str,
) -> Candidate:
    raw_output, generation_meta = generate_synthetic_lr(
        flaw_type=flaw_type,
        difficulty=difficulty,
        client=client,
        model=model,
        prompt_version=prompt_version,
        temperature=temperature,
        correct_position=correct_position,
    )
    payload = parse_synthetic_lr_output(raw_output)
    validation_result = validate_synthetic_lr_payload(payload)

    quality_result = None
    if validation_result.get("status") == "valid":
        quality_result = run_content_quality_checks(payload)

    return {
        "candidate_index": candidate_index,
        "raw_output": raw_output,
        "payload": payload,
        "validation_result": validation_result,
        "quality_result": quality_result,
        "generation_meta": generation_meta,
        "score": _score_candidate(validation_result, quality_result),
    }


def _build_structural_failure_result(candidates: list[dict], include_debug: bool) -> dict:
    first = candidates[0] if candidates else None
    result = {
        "status": "needs_review",
        "stage": "synthetic_structural",
        "errors": first["validation_result"].get("errors", []) if first else ["no_candidates"],
        "record": None,
        "content_quality": None,
        "destination": ("review", "synthetic_structural"),
        "saved_path": None,
        "generation_meta": first["generation_meta"] if first else None,
        "selected_candidate_index": None,
        "selection_summary": {
            "num_candidates": len(candidates),
            "num_valid_candidates": 0,
        },
    }
    if include_debug:
        result["payload"] = first["payload"] if first else {}
        result["candidate_scores"] = [_candidate_debug_summary(c) for c in candidates]
        result["candidates"] = candidates
    return result




def _select_best_candidate(valid_candidates: list[Candidate]) -> Candidate:
    def sort_key(candidate: Candidate):
        q = candidate["quality_result"]
        quality_score = q.score if q is not None else 0
        quality_status_rank = 1 if q is not None and q.status == "pass" else 0
        return (
            candidate["score"],
            quality_status_rank,
            quality_score,
            -candidate["candidate_index"],
        )

    return max(valid_candidates, key=sort_key)


def _score_candidate(validation_result: dict, quality_result) -> int:
    if validation_result.get("status") != "valid":
        return -1

    score = 0
    if quality_result and quality_result.status == "pass":
        score += 50
    if quality_result:
        score += int(quality_result.score * 5)
    return score

def _candidate_debug_summary(candidate: dict) -> dict:
    quality_result = candidate["quality_result"]
    return {
        "candidate_index": candidate["candidate_index"],
        "score": candidate["score"],
        "validation_status": candidate["validation_result"].get("status"),
        "quality_status": quality_result.status if quality_result else None,
        "quality_score": quality_result.score if quality_result else None,
    }

def _apply_quality_result_to_record(record, quality_result) -> None:
    if not quality_result:
        return

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


def run_synthetic_lr_lane(
    *,
    flaw_type: str = "causal",
    difficulty: str = "medium",
    client: LLMClient | None = None,
    model: str | None = None,
    prompt_version: str = "lr_flaw_v2",
    persist: bool = False,
    num_candidates: int = 1,
    include_debug: bool = False,
):
    """Run one synthetic LR item through the canonical lane."""

    client = client or get_llm_client()
    if num_candidates < 1:
        raise ValueError("num_candidates must be >= 1")

    

    candidates = []
    candidate_temps = [0.55, 0.75, 0.95]
    candidate_positions = ["A", "B", "C", "D", "E"]
    random.shuffle(candidate_positions)

    for candidate_index in range(num_candidates):
        temp = candidate_temps[candidate_index % len(candidate_temps)]
        position = candidate_positions[candidate_index % len(candidate_positions)]
        candidates.append(
            _build_candidate(
                candidate_index=candidate_index,
                flaw_type=flaw_type,
                difficulty=difficulty,
                client=client,
                model=model,
                prompt_version=prompt_version,
                temperature=temp,
                correct_position=position,
            )
        )


 

    valid_candidates = [
        c for c in candidates
        if c["validation_result"].get("status") == "valid"
    ]

    if not valid_candidates:
        return _build_structural_failure_result(candidates, include_debug)


    winner = _select_best_candidate(valid_candidates)

    payload = winner["payload"]
    generation_meta = winner["generation_meta"]
    quality_result = winner["quality_result"]

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

    _apply_quality_result_to_record(record, quality_result)


    destination, review_reason = choose_destination(record)
    saved_path = save_record(record, destination, review_reason=review_reason) if persist else None


    result = {
        "status": record.validation.status,
        "stage": "synthetic_canonical",
        "errors": record.validation.errors,
        "record": record,
        "content_quality": {
            "status": quality_result.status if quality_result else None,
            "score": quality_result.score if quality_result else None,
            "flags": quality_result.flags if quality_result else [],
            "metrics": quality_result.metrics if quality_result else {},
        },
        "destination": destination,
        "saved_path": saved_path,
        "generation_meta": generation_meta,
        "selected_candidate_index": winner["candidate_index"],
        "selection_summary": {
            "num_candidates": len(candidates),
            "num_valid_candidates": len(valid_candidates),
        },
    }

    if include_debug:
        result["payload"] = payload
        result["candidate_scores"] = [_candidate_debug_summary(c) for c in candidates]

        
        result["candidates"] = candidates

    return result
