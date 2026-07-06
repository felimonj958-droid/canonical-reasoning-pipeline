import pytest

from src.generate.synthetic_lr import build_synthetic_lr_prompt


def test_build_synthetic_lr_prompt_includes_causal_metadata():
    prompt = build_synthetic_lr_prompt(
        flaw_type="causal",
        difficulty="medium",
    )

    assert "Target flaw type: causal" in prompt
    assert "Target difficulty: medium" in prompt
    assert "treating correlation as causation" in prompt
    assert "Correct: [single letter A-E]" in prompt


def test_build_synthetic_lr_prompt_includes_conditional_guidance():
    prompt = build_synthetic_lr_prompt(
        flaw_type="necessary_vs_sufficient",
        difficulty="hard",
    )

    assert "Target flaw type: necessary_vs_sufficient" in prompt
    assert "Target difficulty: hard" in prompt
    assert "necessary condition" in prompt
    assert "sufficient condition" in prompt


def test_build_synthetic_lr_prompt_rejects_unsupported_flaw_type():
    with pytest.raises(ValueError):
        build_synthetic_lr_prompt(
            flaw_type="sampling",
            difficulty="medium",
        )


def test_build_synthetic_lr_prompt_rejects_unsupported_difficulty():
    with pytest.raises(ValueError):
        build_synthetic_lr_prompt(
            flaw_type="causal",
            difficulty="extreme",
        )
