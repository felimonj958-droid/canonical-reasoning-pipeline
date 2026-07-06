"""LLM-as-judge scoring for a single record."""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Optional

from src.evaluate.judge_rubric import JudgeScore, build_judge_prompt
from src.llm_client import LLMClient, get_llm_client


@dataclass
class JudgeResult:
    """Result of judging one record. Never raises — always returns a status."""

    record_id: str
    status: str  # "scored" | "parse_error" | "runtime_error"
    score: Optional[JudgeScore] = None
    raw_output: str = ""
    error: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_seconds: float = 0.0
    judge_model: str = ""


def _extract_json_block(text: str) -> str:
    """Extract the first {...} JSON object from LLM output, tolerating fences and prose."""
    # Strip markdown fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text)

    # Find first balanced {...}
    start = text.find("{")
    if start == -1:
        return text
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return text[start:]


def judge_record(
    record_dict: dict,
    client: Optional[LLMClient] = None,
    system_prompt: Optional[str] = None,
    judge_model: str = "gpt-4o-mini",
) -> JudgeResult:
    """Score one canonical record with the LLM judge.

    Never raises — returns a JudgeResult with status indicating outcome.
    """
    client = client or get_llm_client()
    record_id = record_dict.get("record_id", "unknown")

    try:
        prompt = build_judge_prompt(record_dict)
    except Exception as exc:
        return JudgeResult(
            record_id=record_id,
            status="runtime_error",
            error=f"prompt_build_failed: {exc}",
        )

    t0 = time.perf_counter()
    try:
        # Use the same generate interface as the generator
        # LLMClient.generate signature: (prompt, system=None, temperature=None, max_tokens=None, ...)
        from src.llm_client.base import GenerationRequest

        req = GenerationRequest(
            prompt=prompt,
            model=judge_model,
            system=system_prompt or "You are a strict LSAT evaluator. Return valid JSON only.",
            temperature=0.0,  # deterministic judging
            max_tokens=400,
        )
        response = client.generate(req)
    except Exception as exc:
        return JudgeResult(
            record_id=record_id,
            status="runtime_error",
            error=f"generate_failed: {type(exc).__name__}: {exc}",
            latency_seconds=time.perf_counter() - t0,
        )

    latency = time.perf_counter() - t0
    raw = response.text
    json_block = _extract_json_block(raw)

    try:
        parsed = json.loads(json_block)
        score = JudgeScore(**parsed)
    except Exception as exc:
        return JudgeResult(
            record_id=record_id,
            status="parse_error",
            raw_output=raw,
            error=f"parse_failed: {type(exc).__name__}: {exc}",
            prompt_tokens=getattr(response, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(response, "completion_tokens", 0) or 0,
            latency_seconds=latency,
            judge_model=getattr(response, "model", "") or "",
        )

    return JudgeResult(
        record_id=record_id,
        status="scored",
        score=score,
        raw_output=raw,
        prompt_tokens=getattr(response, "prompt_tokens", 0) or 0,
        completion_tokens=getattr(response, "completion_tokens", 0) or 0,
        latency_seconds=latency,
        judge_model=getattr(response, "model", "") or "",
    )