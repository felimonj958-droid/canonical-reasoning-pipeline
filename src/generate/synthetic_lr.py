from __future__ import annotations

import re
import subprocess  # kept for legacy tests only; new flow uses LLMClient

from src.llm_client import GenerationRequest, LLMClient, get_llm_client
from src.persist.models import GenerationMeta


SUPPORTED_FLAW_TYPES = {
    "causal",
    "necessary_vs_sufficient",
}

SUPPORTED_DIFFICULTIES = {
    "easy",
    "medium",
    "hard",
}

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")

DEFAULT_PROMPT_VERSION = "lr_flaw_v2"


def build_synthetic_lr_prompt(
    flaw_type: str = "causal",
    difficulty: str = "medium",
    prompt_version: str = DEFAULT_PROMPT_VERSION,
    correct_position: str = "C",
) -> str:
    if flaw_type not in SUPPORTED_FLAW_TYPES:
        raise ValueError(f"Unsupported flaw_type: {flaw_type}")

    if difficulty not in SUPPORTED_DIFFICULTIES:
        raise ValueError(f"Unsupported difficulty: {difficulty}")

    if flaw_type == "causal":
        flaw_guidance = """
Write a Logical Reasoning flaw question in which the argument contains a causal reasoning error.

Use one of these causal-flaw patterns:
- treating correlation as causation
- ignoring an alternative cause
- ignoring possible reverse causation
- inferring a broad causal rule from limited evidence

The correct answer must precisely describe the causal flaw actually committed in the stimulus.
""".strip()

        distractor_guidance = """
Answer choice roles (assign each of the 5 choices to exactly one role):

CORRECT: precisely names the causal flaw actually committed in the stimulus. Uses standard LSAT phrasing (e.g. "takes for granted that a correlation is sufficient to establish causation"; "fails to consider that the causal relationship may run in the opposite direction"; "overlooks the possibility that a third factor causes both").

TRAP-A (adjacent causal flaw): names a DIFFERENT causal flaw than the one committed. If the stimulus commits correlation-as-causation, this distractor might name reverse-causation, or ignoring-an-alternative-cause. The wording sounds causal and LSAT-appropriate, but the flaw named is not the one actually committed.

TRAP-B (right family, wrong scope): names a causal flaw but overreaches or underreaches. Example: "assumes that the causal relationship holds in ALL cases" when the stimulus only claims a single instance, or "concludes that no other factor could contribute" when the stimulus makes a weaker claim.

TRAP-C (surface-plausible non-flaw): describes a real feature of the argument that is NOT the flaw — e.g. "relies on a small sample" when sample size isn't the issue, or "uses ambiguous terminology" when the terms are clear. Must be tempting on skim but not the actual defect.

WEAK: an obviously wrong distractor — either irrelevant to the argument, or a meta-critique like "uses complex language" or "makes an unsupported factual claim" that doesn't attack the reasoning. This is the easiest to eliminate. Every LSAT item has one of these.

The CORRECT position is specified in the Requirements section above. Assign TRAP-A, TRAP-B, TRAP-C, and WEAK to the other four positions in any order. Do NOT label choices with role names in the output.
""".strip()

    elif flaw_type == "necessary_vs_sufficient":
        flaw_guidance = """
Write a Logical Reasoning flaw question in which the argument confuses a necessary condition with a sufficient condition, or reverses a conditional relationship.

Use one of these conditional-flaw patterns:
- treating a necessary condition as if it were sufficient (having condition X is required, therefore having X guarantees the outcome)
- treating a sufficient condition as if it were necessary (X guarantees the outcome, therefore only X can produce the outcome)
- affirming the consequent (if P then Q; Q is true; therefore P)
- denying the antecedent (if P then Q; not P; therefore not Q)

The correct answer must precisely describe the conditional flaw actually committed in the stimulus.
""".strip()

        distractor_guidance = """
Answer choice roles (assign each of the 5 choices to exactly one role):

CORRECT: precisely names the conditional flaw actually committed. Uses standard LSAT phrasing (e.g. "treats a condition that is necessary for X as if it were sufficient for X"; "mistakes a sufficient condition for a necessary one"; "confuses a claim about what must be true with a claim about what is enough to be true").

TRAP-A (adjacent conditional flaw): names the OPPOSITE conditional confusion. If the stimulus confuses necessary-as-sufficient, this distractor names sufficient-as-necessary, or vice versa. Both are conditional flaws, so it sounds right on skim.

TRAP-B (right family, wrong scope): names a conditional flaw but overreaches — e.g. "assumes there is only one way to achieve the outcome" when the argument doesn't claim uniqueness, or "concludes the condition is always required" when the stimulus makes a narrower claim.

TRAP-C (surface-plausible non-flaw): describes something true about the argument that is NOT the flaw — e.g. "generalizes from a single case" when the argument isn't generalizing, or "assumes the audience shares a definition" when the terms are unambiguous.

WEAK: an obviously wrong distractor — irrelevant to the argument, or a meta-critique like "uses emotional appeal" or "relies on outdated evidence" that doesn't attack the conditional reasoning.

The CORRECT position is specified in the Requirements section above. Assign TRAP-A, TRAP-B, TRAP-C, and WEAK to the other four positions in any order. Do NOT label choices with role names in the output.
""".strip()

    else:
        raise ValueError(f"Unsupported flaw_type: {flaw_type}")
    

    difficulty_guidance = """
Difficulty guidance:
- easy: the flaw should be relatively clear, the stimulus should be short, and the wrong answers should be easier to eliminate
- medium: the flaw should be somewhat subtler, with moderate abstraction in the answer choices
- hard: the flaw should be more disguised, and the wrong answers should be more tempting and closely related
""".strip()

    stem_guidance = """
Use an LSAT-style flaw question stem. Prefer one of these forms:
- Which one of the following most accurately describes a flaw in the argument?
- The reasoning in the argument is most vulnerable to criticism on the grounds that it
- Which one of the following most accurately expresses the flaw in the reasoning above?
""".strip()

    format_guidance = """
Output format exactly:

Stimulus:
[2-5 sentences presenting an argument]

Question:
[one LSAT-style flaw question stem]

Choices:
A. [choice text]
B. [choice text]
C. [choice text]
D. [choice text]
E. [choice text]

Correct: [single letter A-E]
""".strip()

    return f"""You are an expert LSAT Logical Reasoning writer.

Generate ONE synthetic LSAT Logical Reasoning flaw question.

Target flaw type: {flaw_type}
Target difficulty: {difficulty}
Prompt version: {prompt_version}

Requirements:
- Write one short stimulus containing an argument, not a mere description.
- The flaw must match the target flaw type.
- Use exactly one LSAT-style flaw question stem.
- Provide exactly five answer choices labeled A through E.
- Each of the five choices must fill a distinct role from the distractor guidance below.
- Place the CORRECT answer at position {correct_position}. The other four positions receive the TRAP-A, TRAP-B, TRAP-C, and WEAK roles in any order.
- Distractors must attack the SAME reasoning family as the correct answer (do not use unrelated flaws like "anecdotal evidence" unless one is designated as WEAK).
- Provide exactly one correct answer.
- Do not include any explanation.
- Do not include markdown.
- Keep everything in plain text.
- Follow the output format exactly.

{stem_guidance}

{difficulty_guidance}

{flaw_guidance}

{distractor_guidance}

{format_guidance}
""".strip()


def clean_synthetic_lr_output(text: str) -> str:
    cleaned = ANSI_ESCAPE_RE.sub("", text or "")

    stimulus_index = cleaned.find("Stimulus:")
    if stimulus_index != -1:
        cleaned = cleaned[stimulus_index:]

    cleaned = cleaned.replace("...done thinking.", "")
    cleaned = cleaned.strip()

    return cleaned


def generate_synthetic_lr(
    flaw_type: str = "causal",
    difficulty: str = "medium",
    *,
    client: LLMClient | None = None,
    prompt_version: str = DEFAULT_PROMPT_VERSION,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    model: str | None = None,
    correct_position: str | None = None,
) -> tuple[str, GenerationMeta]:
    """Generate one synthetic LR item via the provided LLMClient.

    Returns (cleaned_text, generation_metadata). The metadata is designed
    to attach to the canonical record's `generation` field.

    Backward compatibility: legacy callers passing `model=` as a positional
    or keyword hint can still do so; the client resolves the actual model
    used and records it on the returned metadata.
    """
    import random
    client = client or get_llm_client()

    if correct_position is None:
        correct_position = random.choice(["A", "B", "C", "D", "E"])
    correct_position = correct_position.upper()
    if correct_position not in {"A", "B", "C", "D", "E"}:
        raise ValueError(f"correct_position must be A-E, got {correct_position}")

    prompt = build_synthetic_lr_prompt(
        flaw_type=flaw_type,
        difficulty=difficulty,
        prompt_version=prompt_version,
        correct_position=correct_position,
    )

    request = GenerationRequest(
        prompt=prompt,
        model=model or getattr(client, "default_model", ""),
        temperature=temperature,
        max_tokens=max_tokens,
    )
    response = client.generate(request)

    cleaned = clean_synthetic_lr_output(response.text)

    meta = GenerationMeta(
        backend=response.backend,
        model=response.model,
        flaw_type=flaw_type,
        difficulty=difficulty,
        prompt_version=prompt_version,
        temperature=temperature,
        max_tokens=max_tokens,
        prompt_tokens=response.prompt_tokens,
        completion_tokens=response.completion_tokens,
        latency_seconds=response.latency_seconds,
    )
    return cleaned, meta


def generate_synthetic_lr_via_subprocess(
    model: str = "qwen3:8b",
    flaw_type: str = "causal",
    difficulty: str = "medium",
) -> str:
    """Legacy subprocess-based Ollama call.

    Preserved only for tests or scripts that shell out to `ollama run`
    directly. New code should use `generate_synthetic_lr(client=...)`.
    """
    prompt = build_synthetic_lr_prompt(
        flaw_type=flaw_type,
        difficulty=difficulty,
        prompt_version=DEFAULT_PROMPT_VERSION,
    )

    try:
        result = subprocess.run(
            ["ollama", "run", model, prompt],
            capture_output=True,
            text=True,
            check=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Ollama generation timed out") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Ollama generation failed: {exc.stderr}") from exc

    return clean_synthetic_lr_output(result.stdout.strip())


def parse_synthetic_lr_output(text: str) -> dict:
    cleaned_text = clean_synthetic_lr_output(text)

    stimulus_match = re.search(
        r"Stimulus:\s*(.*?)\s*Question:",
        cleaned_text,
        flags=re.DOTALL,
    )
    question_match = re.search(
        r"Question:\s*(.*?)\s*Choices:",
        cleaned_text,
        flags=re.DOTALL,
    )
    correct_match = re.search(
        r"Correct:\s*([A-E])\b",
        cleaned_text,
        flags=re.IGNORECASE,
    )

    choice_matches = re.findall(
        r"^\s*([A-E])\.\s*(.+?)\s*$",
        cleaned_text,
        flags=re.MULTILINE,
    )

    return {
        "stimulus": stimulus_match.group(1).strip() if stimulus_match else "",
        "question": question_match.group(1).strip() if question_match else "",
        "answer_choices": [
            {"label": label, "text": choice_text.strip()}
            for label, choice_text in choice_matches
        ],
        "correct_answer": correct_match.group(1).upper() if correct_match else "",
        "raw_output": cleaned_text,
    }