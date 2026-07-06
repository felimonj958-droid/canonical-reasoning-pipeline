from __future__ import annotations

from dataclasses import dataclass, field
import re


META_PATTERNS = [
    r"\bas an ai\b",
    r"\bhere is (a|your)\b",
    r"\bcorrect answer\b",
    r"\bthe correct answer\b",
    r"\bexplanation\b",
    r"\bi chose\b",
    r"\bthe answer is\b",
    r"^stimulus\s*:",
    r"^question\s*:",
    r"^choices?\s*:",
]

ARGUMENT_SIGNALS = [
    "therefore",
    "thus",
    "hence",
    "so",
    "consequently",
    "because",
    "since",
    "after all",
    "for this reason",
    "clearly",
    "must",
    "should",
    "probably",
    "likely",
]

LSAT_STEM_PATTERNS = [
    r"which one of the following.*describes a flaw",
    r"which one of the following.*expresses the flaw",
    r"which one of the following.*most accurately.*flaw",
    r"the reasoning in the argument is most vulnerable to criticism",
    r"the argument is most vulnerable to criticism",
    r"which one of the following.*most strongly supports",
    r"which one of the following.*most strongly weakens",
    r"which one of the following.*assumption",
    r"which one of the following.*most logically completes",
    r"which one of the following.*can be properly inferred",
    r"which one of the following.*can be most reasonably inferred",
    r"which one of the following.*principle",
    r"which one of the following.*parallel reasoning",
]




@dataclass
class ContentQualityResult:
    status: str
    score: float
    flags: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)


def run_content_quality_checks(payload: dict) -> ContentQualityResult:
    stimulus = (payload.get("stimulus") or "").strip()
    question = (payload.get("question") or "").strip()
    choices = payload.get("answer_choices") or []

    flags: list[str] = []
    warnings: list[str] = []
    metrics: dict = {}

    flags.extend(check_lengths(stimulus, question, choices, metrics))
    flags.extend(check_meta_language(stimulus, question, choices))
    flags.extend(check_question_style(question))
    flags.extend(check_argument_signals(stimulus, metrics))
    flags.extend(check_choice_quality(choices, metrics))

    score = compute_quality_score(flags)

    hard_fail_flags = {
        "meta_language_detected",
        "formatting_artifact_detected",
        "near_duplicate_choices",
    }

    status = "review" if hard_fail_flags.intersection(flags) else (
        "pass" if score >= 0.70 else "review"
    )


    return ContentQualityResult(
        status=status,
        score=score,
        flags=sorted(set(flags)),
        warnings=warnings,
        metrics=metrics,
    )


def check_lengths(
    stimulus: str,
    question: str,
    choices: list[dict],
    metrics: dict,
) -> list[str]:
    flags: list[str] = []

    stimulus_len = len(stimulus)
    question_len = len(question)
    choice_lengths = {
        choice.get("label", f"choice_{idx}"): len((choice.get("text") or "").strip())
        for idx, choice in enumerate(choices)
    }

    metrics["stimulus_char_count"] = stimulus_len
    metrics["question_char_count"] = question_len
    metrics["choice_char_counts"] = choice_lengths

    if stimulus_len < 15:
        flags.append("stimulus_too_short")
    if stimulus_len > 1200:
        flags.append("stimulus_too_long")

    if question_len < 20:
        flags.append("question_too_short")
    if question_len > 300:
        flags.append("question_too_long")

    if choice_lengths:
        min_len = min(choice_lengths.values())
        max_len = max(choice_lengths.values())
        metrics["min_choice_char_count"] = min_len
        metrics["max_choice_char_count"] = max_len
        metrics["choice_length_ratio"] = (
            round(max_len / min_len, 2) if min_len > 0 else None
        )

        if min_len < 3:
            flags.append("choice_too_short")
        if max_len > 300:
            flags.append("choice_too_long")
        if min_len > 0 and (max_len / min_len) > 4.0:
            flags.append("choice_length_imbalance")

    return flags



def check_meta_language(
    stimulus: str,
    question: str,
    choices: list[dict],
) -> list[str]:
    flags: list[str] = []

    combined_parts = [stimulus, question]
    combined_parts.extend((choice.get("text") or "") for choice in choices)
    combined = "\n".join(combined_parts).lower()

    for pattern in META_PATTERNS:
        if re.search(pattern, combined, flags=re.MULTILINE):
            flags.append("meta_language_detected")
            break

    if "```" in combined or "#" in combined:
        flags.append("formatting_artifact_detected")

    return flags


def check_question_style(question: str) -> list[str]:
    normalized = (question or "").lower().strip()

    if not normalized:
        return ["question_not_lsat_style"]

    for pattern in LSAT_STEM_PATTERNS:
        if re.search(pattern, normalized):
            return []

    return ["question_not_lsat_style"]



def check_argument_signals(stimulus: str, metrics: dict) -> list[str]:
    normalized = stimulus.lower()
    signal_hits = [signal for signal in ARGUMENT_SIGNALS if signal in normalized]
    metrics["argument_signal_count"] = len(signal_hits)
    metrics["argument_signals_found"] = signal_hits

    if len(signal_hits) == 0 and len(normalized) > 120:
        return ["weak_argument_signals"]


    return []


def check_choice_quality(choices: list[dict], metrics: dict) -> list[str]:
    flags: list[str] = []

    texts = [(choice.get("text") or "").strip().lower() for choice in choices]
    cleaned_texts = [text for text in texts if text]

    if len(cleaned_texts) != len(set(cleaned_texts)):
        flags.append("near_duplicate_choices")

    first_words = []
    for text in cleaned_texts:
        tokens = text.split()
        first_words.append(" ".join(tokens[:4]))

    if first_words and len(set(first_words)) == 1:
        flags.append("choices_share_opening_phrase")

    metrics["choice_count"] = len(choices)

    return flags


def compute_quality_score(flags: list[str]) -> float:
    penalty_map = {
        "stimulus_too_short": 0.20,
        "stimulus_too_long": 0.10,
        "question_too_short": 0.15,
        "question_too_long": 0.10,
        "choice_too_short": 0.15,
        "choice_too_long": 0.10,
        "choice_length_imbalance": 0.15,
        "meta_language_detected": 0.35,
        "formatting_artifact_detected": 0.20,
        "question_not_lsat_style": 0.20,
        "weak_argument_signals": 0.15,
        "near_duplicate_choices": 0.25,
        "choices_share_opening_phrase": 0.10,
    }

    score = 1.0
    for flag in set(flags):
        score -= penalty_map.get(flag, 0.05)

    return max(0.0, round(score, 2))
