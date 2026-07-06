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

DEFAULT_PROMPT_VERSION = "lr_flaw_v1"


def build_synthetic_lr_prompt(
    flaw_type: str = "causal",
    difficulty: str = "medium",
    prompt_version: str = DEFAULT_PROMPT_VERSION,
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

The correct answer must precisely describe the causal flaw.
The wrong answers should be plausible LSAT-style flaw descriptions, but they must not match the stimulus.
""".strip()
    elif flaw_type == "necessary_vs_sufficient":
        flaw_guidance = """
Write a Logical Reasoning flaw question in which the argument confuses a necessary condition with a sufficient condition, or reverses a conditional relationship.

The correct answer must precisely describe the conditional flaw.
The wrong answers should be plausible LSAT-style flaw descriptions, but they must not match the stimulus.
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
- Provide exactly one correct answer.
- Do not include any explanation.
- Do not include markdown.
- Keep everything in plain text.
- Follow the output format exactly.

{stem_guidance}

{difficulty_guidance}

{flaw_guidance}

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
) -> tuple[str, GenerationMeta]:
    """Generate one synthetic LR item via the provided LLMClient.

    Returns (cleaned_text, generation_metadata). The metadata is designed
    to attach to the canonical record's `generation` field.

    Backward compatibility: legacy callers passing `model=` as a positional
    or keyword hint can still do so; the client resolves the actual model
    used and records it on the returned metadata.
    """
    client = client or get_llm_client()
    prompt = build_synthetic_lr_prompt(
        flaw_type=flaw_type,
        difficulty=difficulty,
        prompt_version=prompt_version,
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