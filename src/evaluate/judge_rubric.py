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


JUDGE_PROMPT_TEMPLATE = """You are a strict LSAT prep expert evaluating a synthetic Logical Reasoning item against real LSAT quality.

CALIBRATION RULES:
- Score against REAL LSAT items, not a curve of synthetic items.
- Reserve 5 for items indistinguishable from an official LSAT question.
- Reserve 4 for items that would pass a professional LSAT prep review with minor edits.
- Score 3 for items that are recognizably LSAT-shaped but have real weaknesses.
- Score 1-2 for items with structural or logical defects.
- If you are uncertain between two adjacent scores, choose the LOWER one.
- It is expected that many synthetic items will score 3 or lower. Do not inflate.

Score each of these 5 dimensions (integers 1-5):

1. argument_coherence
   1 = premises and conclusion do not connect; argument is incoherent
   2 = argument is followable but has gaps or unclear structure
   3 = argument works but is bland, over-broad, or relies on vague terms
   4 = clean premise-to-conclusion structure with LSAT-appropriate compactness
   5 = tight, elegant argument matching official LSAT phrasing and density

2. flaw_fidelity (claimed flaw type: {flaw_type})
   1 = argument does not commit the claimed flaw at all
   2 = argument gestures at the flaw but does not instantiate it
   3 = argument commits the flaw weakly or with muddled premises
   4 = argument commits the flaw clearly with minor slippage
   5 = textbook instance of the claimed flaw, comparable to real LSAT items

3. question_stem_quality
   1 = stem is malformed, missing, or not an LSAT stem
   2 = stem is LSAT-adjacent but awkward or non-standard
   3 = stem uses a valid LSAT template but has small phrasing issues
   4 = stem is a clean, standard LSAT flaw-question stem
   5 = stem is verbatim or near-verbatim LSAT phrasing

4. distractor_plausibility
   1 = distractors are obviously wrong or nonsensical
   2 = distractors are mostly easy to eliminate on skim
   3 = at least one distractor is tempting; others are weak
   4 = most distractors are tempting and defeatable on analysis
   5 = distractors mirror real LSAT trap patterns (partial truth, wrong scope, right idea/wrong flaw)

5. correct_answer_precision
   1 = correct answer is wrong, ambiguous, or restates the stimulus
   2 = correct answer names the wrong flaw or is too broad
   3 = correct answer names the flaw but is imprecise or overreaches
   4 = correct answer identifies the flaw cleanly with minor imprecision
   5 = correct answer surgically names the flaw in LSAT-style phrasing

Return ONLY a JSON object (no markdown fences, no prose before or after):
{{
  "argument_coherence": <int 1-5>,
  "flaw_fidelity": <int 1-5>,
  "question_stem_quality": <int 1-5>,
  "distractor_plausibility": <int 1-5>,
  "correct_answer_precision": <int 1-5>,
  "notes": "<one-sentence rationale citing the weakest dimension>"
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

    # Support both nested (canonical) and flat structures.
    content = record_dict.get("content") or {}

    stimulus = (content.get("stimulus") or record_dict.get("stimulus") or "").strip()
    question = (
        content.get("question_stem")
        or record_dict.get("question")
        or record_dict.get("question_stem")
        or ""
    ).strip()
    correct_raw = content.get("correct_answer") or record_dict.get("correct_answer") or ""
    correct = str(correct_raw).strip()
    choices = content.get("answer_choices") or record_dict.get("answer_choices") or []
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