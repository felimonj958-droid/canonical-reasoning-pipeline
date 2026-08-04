"""Rubric definition and judge prompt for LLM-as-judge evaluation.

The rubric has 5 dimensions scored 1-5 each. Total score range: 5-25.
A record scoring >= 20 is considered "high quality" for portfolio metrics.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


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


def _resolve_canonical_metadata(record_dict: dict) -> tuple[str, str]:
    metadata = record_dict.get("metadata") or {}
    generation = record_dict.get("generation") or {}
    lsat = record_dict.get("lsat") or {}

    flaw_type = (
        metadata.get("flaw_type")
        or metadata.get("question_type")
        or record_dict.get("flaw_type")
        or generation.get("flaw_type")
        or lsat.get("question_type")
        or "unknown"
    )

    difficulty = (
        metadata.get("difficulty")
        or record_dict.get("difficulty")
        or generation.get("difficulty")
        or lsat.get("difficulty")
        or "unknown"
    )

    return str(flaw_type), str(difficulty)


JUDGE_PROMPT_TEMPLATE = """You are a strict LSAT prep expert evaluating a synthetic Logical Reasoning item against real LSAT quality.

CALIBRATION RULES:
- Score the item against the canonical flaw_type stored in metadata, not against whichever surface wording looks closest.
- If the item is mislabeled, penalize flaw_fidelity even when the stimulus is otherwise coherent.
- Distinguish causal, necessary_vs_sufficient, and sampling as separate flaw families.
- Penalize answer choices that are memorable because they reuse the same flaw phrasing across items rather than because they require reasoning.

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
   - causal: conclude causation from correlation, sequence, or weak evidence.
   - necessary_vs_sufficient: treat a requirement as enough, or a condition as guaranteed.
   - sampling: generalize from a sample without support for representativeness.

3. question_stem_quality
   1 = stem is malformed, missing, or not an LSAT stem
   2 = stem is LSAT-adjacent but awkward or non-standard
   3 = stem uses a valid LSAT template but has small phrasing issues or feels mechanically slotted into a weak item
   4 = stem is a clean, standard LSAT flaw-question stem
   5 = stem is verbatim or near-verbatim LSAT phrasing and fits the item naturally

4. distractor_plausibility
   1 = distractors are obviously wrong, formulaic, or distinguishable by surface pattern alone
   2 = distractors are mostly easy to eliminate on skim because of repetitive wording, genericity, or template-like structure
   3 = at least one distractor is tempting, but answer-choice phrasing still gives away the item too easily
   4 = most distractors are tempting and require close reasoning to defeat; wording is varied enough to avoid template recognition
   5 = distractors mirror real LSAT trap patterns while remaining non-repetitive, interpretation-sensitive, and distinguishable only through careful logical analysis

5. correct_answer_precision
   1 = correct answer is wrong, ambiguous, or restates the stimulus
   2 = correct answer names the wrong flaw or is too broad
   3 = correct answer names the flaw but is imprecise or overreaches
   4 = correct answer identifies the flaw cleanly with minor imprecision
   5 = correct answer surgically names the flaw in LSAT-style phrasing and is identifiable because it best captures the actual reasoning flaw, not because the other choices are formulaic, repetitive, or mechanically eliminable

Return ONLY a JSON object (no markdown fences, no prose before or after):
{{
  "argument_coherence": <int 1-5>,
  "flaw_fidelity": <int 1-5>,
  "question_stem_quality": <int 1-5>,
  "distractor_plausibility": <int 1-5>,
  "correct_answer_precision": <int 1-5>,
  "notes": "<one-sentence rationale citing the weakest dimension; mention if the item is too template-like, if choices are memorably repetitive, or if the item rewards pattern recognition over reasoning>"
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
    flaw_type, difficulty = _resolve_canonical_metadata(record_dict)

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
