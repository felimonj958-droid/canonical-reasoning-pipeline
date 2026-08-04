import pytest

from src.generate.synthetic_lr import (
    build_synthetic_lr_prompt,
    clean_synthetic_lr_output,
    parse_synthetic_lr_output,
)


class TestBuildSyntheticLRPrompt:
    def test_includes_causal_metadata_and_guidance(self):
        prompt = build_synthetic_lr_prompt(
            flaw_type="causal",
            difficulty="medium",
        )

        assert "Target flaw type: causal" in prompt
        assert "Target difficulty: medium" in prompt
        assert "treating correlation as causation" in prompt
        assert "Correct: [single letter A-E]" in prompt

    def test_includes_conditional_guidance(self):
        prompt = build_synthetic_lr_prompt(
            flaw_type="necessary_vs_sufficient",
            difficulty="hard",
        )

        assert "Target flaw type: necessary_vs_sufficient" in prompt
        assert "Target difficulty: hard" in prompt
        assert "necessary condition" in prompt
        assert "sufficient condition" in prompt

    def test_includes_sampling_guidance(self):
        prompt = build_synthetic_lr_prompt(
            flaw_type="sampling",
            difficulty="medium",
        )

        assert "Target flaw type: sampling" in prompt
        assert "Target difficulty: medium" in prompt
        assert "sampling-flaw patterns" in prompt
        assert "unrepresentative" in prompt
        assert "Correct: [single letter A-E]" in prompt


    def test_rejects_unsupported_difficulty(self):
        with pytest.raises(ValueError):
            build_synthetic_lr_prompt(
                flaw_type="causal",
                difficulty="extreme",
            )


class TestCleanSyntheticLROutput:
    def test_removes_thinking_and_ansi(self):
        raw = (
            "Thinking...\n"
            "some scratch text\n"
            "...done thinking.\n\n"
            "Stimulus:\n"
            "A study found that coffee drinkers are more likely to develop heart disease.\x1b[K\n"
            "Therefore, coffee causes heart disease.\n\n"
            "Question:\n"
            "The reasoning in the argument is most vulnerable to criticism on the grounds that it\x1b[6D\x1b[K\n\n"
            "Choices:\n"
            "A. assumes a causal relationship based solely on a correlation\x1b[K\n"
            "B. overlooks a possibility\n"
            "C. confuses a necessary condition with a sufficient one\n"
            "D. generalizes from one case\n"
            "E. uses an ambiguous term\n\n"
            "Correct: A\n"
        )

        cleaned = clean_synthetic_lr_output(raw)

        assert "Thinking..." not in cleaned
        assert "...done thinking." not in cleaned
        assert "\x1b" not in cleaned
        assert cleaned.startswith("Stimulus:")


class TestParseSyntheticLROutput:
    def test_uses_cleaned_text(self):
        raw = (
            "Thinking...\n"
            "...done thinking.\n"
            "Stimulus:\n"
            "To pass the course, you must attend all lectures.\x1b[K Therefore, attending all lectures will guarantee that you pass the course.\n"
            "Question:\n"
            "The reasoning in the argument is most vulnerable to criticism on the grounds that it\x1b[K\n"
            "Choices:\n"
            "A. assumes that correlation implies causation\n"
            "B. generalizes from a single instance\n"
            "C. treats a necessary condition as a sufficient one\n"
            "D. overlooks the possibility of alternative causes\n"
            "E. commits a false dilemma fallacy\n"
            "Correct: C\n"
        )

        parsed = parse_synthetic_lr_output(raw)

        assert parsed["stimulus"].startswith("To pass the course")
        assert parsed["question"].startswith("The reasoning in the argument")
        assert parsed["correct_answer"] == "C"
        assert len(parsed["answer_choices"]) == 5
        assert "\x1b" not in parsed["raw_output"]
