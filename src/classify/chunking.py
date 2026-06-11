from __future__ import annotations

from typing import Any, Dict, List

from transformers import AutoTokenizer


DEFAULT_TOKENIZER = "distilbert-base-uncased"


def load_tokenizer(model_name: str = DEFAULT_TOKENIZER):
    return AutoTokenizer.from_pretrained(model_name, use_fast=True)


def count_tokens(text: str, tokenizer) -> int:
    if not text:
        return 0
    return len(tokenizer.encode(text, add_special_tokens=True))


def build_classification_text(record: Dict[str, Any], goal: str = "document_type") -> str:
    parts: List[str] = []

    if goal:
        parts.append(f"goal: {goal}")

    record_id = record.get("record_id")
    if record_id:
        parts.append(f"record_id: {record_id}")

    source = record.get("source", {}) or {}
    lsat = record.get("lsat", {}) or {}
    content = record.get("content", {}) or {}

    source_file = source.get("source_file")
    modality = source.get("modality")

    if modality:
        parts.append(f"modality: {modality}")
    if source_file:
        parts.append(f"source_file: {source_file}")

    exam = lsat.get("exam")
    prep_test = lsat.get("prep_test")
    section = lsat.get("section")
    section_number = lsat.get("section_number")
    question_number = lsat.get("question_number")
    question_type = lsat.get("question_type")
    difficulty = lsat.get("difficulty")

    if exam:
        parts.append(f"exam: {exam}")
    if prep_test:
        parts.append(f"prep_test: {prep_test}")
    if section:
        parts.append(f"section: {section}")
    if section_number is not None:
        parts.append(f"section_number: {section_number}")
    if question_number is not None:
        parts.append(f"question_number: {question_number}")
    if question_type:
        parts.append(f"question_type: {question_type}")
    if difficulty:
        parts.append(f"difficulty: {difficulty}")

    passage = content.get("passage")
    stimulus = content.get("stimulus")
    question_stem = content.get("question_stem")
    explanation = content.get("explanation")
    correct_answer = content.get("correct_answer")
    raw_text = content.get("raw_text")
    normalized_text = content.get("normalized_text")

    if passage:
        parts.append(f"passage: {passage}")
    if stimulus:
        parts.append(f"stimulus: {stimulus}")
    if question_stem:
        parts.append(f"question_stem: {question_stem}")

    answer_choices = content.get("answer_choices") or []
    rendered_choices: List[str] = []

    for choice in answer_choices:
        if not isinstance(choice, dict):
            rendered_choices.append(str(choice).strip())
            continue

        label = choice.get("label")
        text = (choice.get("text") or "").strip()

        if not text:
            continue

        if label:
            rendered_choices.append(f"{label}. {text}")
        else:
            rendered_choices.append(text)

    if rendered_choices:
        parts.append("answer_choices: " + " | ".join(rendered_choices))

    if correct_answer:
        parts.append(f"correct_answer: {correct_answer}")
    if explanation:
        parts.append(f"explanation: {explanation}")

    full_text = normalized_text or raw_text
    if full_text:
        parts.append("full_text: " + full_text)

    return "\n".join(parts).strip()


def chunk_text(
    text: str,
    tokenizer,
    max_tokens: int = 384,
    overlap_tokens: int = 64,
) -> List[Dict[str, Any]]:
    if not text or not text.strip():
        return []

    if overlap_tokens >= max_tokens:
        raise ValueError("overlap_tokens must be smaller than max_tokens")

    encoded = tokenizer(
        text,
        add_special_tokens=False,
        return_offsets_mapping=True,
        truncation=False,
    )

    input_ids = encoded["input_ids"]
    offsets = encoded["offset_mapping"]

    if not input_ids:
        return []

    chunks: List[Dict[str, Any]] = []
    step = max_tokens - overlap_tokens
    start = 0
    chunk_index = 0

    while start < len(input_ids):
        end = min(start + max_tokens, len(input_ids))

        char_start = offsets[start][0]
        char_end = offsets[end - 1][1]
        chunk_text_value = text[char_start:char_end].strip()

        chunks.append(
            {
                "chunk_index": chunk_index,
                "token_start": start,
                "token_end": end,
                "token_count": end - start,
                "char_start": char_start,
                "char_end": char_end,
                "text": chunk_text_value,
            }
        )

        if end == len(input_ids):
            break

        start += step
        chunk_index += 1

    return chunks


def choose_strategy(
    token_count: int,
    has_late_evidence: bool = False,
    single_window_tokens: int = 384,
    soft_limit_tokens: int = 512,
) -> Dict[str, Any]:
    if token_count <= single_window_tokens:
        return {
            "strategy": "single_window",
            "reason": "fits comfortably in single window",
            "near_limit": False,
        }

    if token_count <= soft_limit_tokens:
        return {
            "strategy": "single_window",
            "reason": "fits but is near context limit",
            "near_limit": True,
        }

    if has_late_evidence:
        return {
            "strategy": "chunked_hierarchical",
            "reason": "content exceeds window and likely contains late evidence",
            "near_limit": False,
        }

    return {
        "strategy": "chunked",
        "reason": "content exceeds single-window limit",
        "near_limit": False,
    }


def prepare_classification_payload(
    record: Dict[str, Any],
    tokenizer,
    goal: str = "document_type",
    max_tokens: int = 384,
    overlap_tokens: int = 64,
    soft_limit_tokens: int = 512,
) -> Dict[str, Any]:
    text = build_classification_text(record, goal=goal)
    token_count = count_tokens(text, tokenizer)

    late_markers = [
        "answer_choices:",
        "correct_answer:",
        "explanation:",
    ]
    has_late_evidence = any(marker in text[max(0, len(text) // 2):] for marker in late_markers)

    strategy = choose_strategy(
        token_count=token_count,
        has_late_evidence=has_late_evidence,
        single_window_tokens=max_tokens,
        soft_limit_tokens=soft_limit_tokens,
    )

    payload: Dict[str, Any] = {
        "goal": goal,
        "token_count": token_count,
        "strategy": strategy["strategy"],
        "strategy_reason": strategy["reason"],
        "near_limit": strategy["near_limit"],
        "text": text,
    }

    if strategy["strategy"] == "single_window":
        payload["chunks"] = [
            {
                "chunk_index": 0,
                "token_start": 0,
                "token_end": token_count,
                "token_count": token_count,
                "char_start": 0,
                "char_end": len(text),
                "text": text,
            }
        ]
    else:
        payload["chunks"] = chunk_text(
            text=text,
            tokenizer=tokenizer,
            max_tokens=max_tokens,
            overlap_tokens=overlap_tokens,
        )

    return payload
