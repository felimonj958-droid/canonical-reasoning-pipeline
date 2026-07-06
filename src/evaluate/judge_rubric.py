"""Rubric definition and judge prompt for LLM-as-judge evaluation.

The rubric has 5 dimensions scored 1-5 each. Total score range: 5-25.
A record scoring >= 20 is considered "high quality" for portfolio metrics.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


RUBRIC_DIMENSIONS = [
    "argument_coherence",
    "flaw_fidelity",
    "question_stem_quality",
    "distractor_plausibility",
    "correct_answer_precision",
]

HIGH_QUALITY_THRESHOLD = 20  # out of 25


class JudgeScore(BaseModel):
    """Parsed output from the LLM judge for one record."""

    argument_coherence: int = Field(ge=1, le=5)
    flaw_fidelity: int = Field(ge=1, le=5)
    question_stem_quality: int = Field(ge=1, le=5)
    distractor_plausibility: int = Field(ge=1, le=5)
    correct_answer_precision: int = Field(ge=1, le=5)
    notes: str = ""

    @property
    def total(self) -> int:
        return (
            self.argument_coherence
            + self.flaw_fidelity
            + self.question_stem_quality
            + self.distractor_plausibility
            + self.correct_answer_precision
        )

    @property
    def is_high_quality(self) -> bool:
        return self.total >= HIGH_QUALITY_THRESHOLD

    def to_dimensions(self) -> dict[str, int]:
        """Return the 5 rubric dimensions as a dict (no notes, no total)."""
        return {dim: getattr(self, dim) for dim in RUBRIC_DIMENSIONS}


JUDGE_PROMPT_TEMPLATE = """You are an expert LSAT tutor evaluating a synthetically generated Logical Reasoning item.

Score this item on 5 dimensions (1=poor, 5=excellent):

1. argument_coherence: Does the stimulus present a followable argument with clear premises and conclusion?
2. flaw_fidelity: Does the argument actually commit the claimed flaw type ({flaw_type})?
3. question_stem_quality: Is the question stem phrased authentically for the LSAT?
4. distractor_plausibility: Are the incorrect answers tempting but defeatable (not obviously wrong)?
5. correct_answer_precision: Does the correct answer cleanly identify the flaw without overreach?

Return ONLY a JSON object with this exact schema (no markdown fences, no prose):
{{
  "argument_coherence": <int 1-5>,
  "flaw_fidelity": <int 1-5>,
  "question_stem_quality": <int 1-5>,
  "distractor_plausibility": <int 1-5>,
  "correct_answer_precision": <int 1-5>,
  "notes": "<one-sentence rationale>"
}}

--- ITEM ---
Flaw type: {flaw_type}
Difficulty: {difficulty}

Stimulus:
{stimulus}

Question:
{question}

Answer choices:
{answer_choices}

Correct answer: {correct_answer}
"""


def build_judge_prompt(record_dict: dict) -> str:
    """Build the judge prompt from a canonical record dict.

    Accepts either a full CanonicalRecord.model_dump() or a subset with the
    required fields: stimulus, question, answer_choices, correct_answer,
    generation (with flaw_type + difficulty), or a top-level flaw_type/difficulty.
    """
    # Handle both nested (canonical) and flat structures
    gen = record_dict.get("generation") or {}
    flaw_type = record_dict.get("flaw_type") or gen.get("flaw_type") or "unknown"
    difficulty = record_dict.get("difficulty") or gen.get("difficulty") or "unknown"

    stimulus = record_dict.get("stimulus", "").strip()
    question = record_dict.get("question", "").strip()
    correct = record_dict.get("correct_answer", "").strip()

    choices = record_dict.get("answer_choices", [])
    choices_str = "\n".join(
        f"{c.get('label', '?')}. {c.get('text', '').strip()}" for c in choices
    )

    return JUDGE_PROMPT_TEMPLATE.format(
        flaw_type=flaw_type,
        difficulty=difficulty,
        stimulus=stimulus,
        question=question,
        answer_choices=choices_str,
        correct_answer=correct,
    )