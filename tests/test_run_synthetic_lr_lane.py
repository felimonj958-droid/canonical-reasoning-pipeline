from src.normalize.run_synthetic_lr_lane import run_synthetic_lr_lane
from src.persist.models import GenerationMeta


def _fake_generation_meta(**kwargs):
    return GenerationMeta(
        backend="fake",
        model="gpt-4o-mini",
        flaw_type=kwargs.get("flaw_type", "causal"),
        difficulty=kwargs.get("difficulty", "medium"),
        prompt_version=kwargs.get("prompt_version", "lr_flaw_v1"),
        temperature=0.7,
        max_tokens=1024,
    )


class TestRunSyntheticLRLane:
    def test_returns_canonical_record_for_valid_payload(self, monkeypatch):
        raw_output = """Stimulus: A city council member argues that because traffic decreased after one downtown street was closed, the city should close more streets to reduce traffic overall.

Question: Which one of the following most accurately describes a flaw in the council member's reasoning?

A. It treats a result observed in one case as though it must occur in all similar cases.
B. It rejects a proposal solely because the proposal is unpopular.
C. It confuses a necessary condition with a sufficient condition.
D. It relies on ambiguous language in the phrase "reduce traffic overall."
E. It draws a conclusion that simply restates one of its premises.

Correct: A
"""

        parsed_payload = {
            "stimulus": "A city council member argues that because traffic decreased after one downtown street was closed, the city should close more streets to reduce traffic overall.",
            "question": "Which one of the following most accurately describes a flaw in the council member's reasoning?",
            "answer_choices": [
                {"label": "A", "text": "It treats a result observed in one case as though it must occur in all similar cases."},
                {"label": "B", "text": "It rejects a proposal solely because the proposal is unpopular."},
                {"label": "C", "text": "It confuses a necessary condition with a sufficient condition."},
                {"label": "D", "text": 'It relies on ambiguous language in the phrase "reduce traffic overall."'},
                {"label": "E", "text": "It draws a conclusion that simply restates one of its premises."},
            ],
            "correct_answer": "A",
            "raw_output": raw_output,
        }

        monkeypatch.setattr(
            "src.normalize.run_synthetic_lr_lane.generate_synthetic_lr",
            lambda **kwargs: (raw_output, _fake_generation_meta(**kwargs)),
        )
        monkeypatch.setattr(
            "src.normalize.run_synthetic_lr_lane.parse_synthetic_lr_output",
            lambda text: parsed_payload,
        )

        result = run_synthetic_lr_lane()

        assert result["status"] == "valid"
        assert result["stage"] == "synthetic_canonical"
        assert result["errors"] == []
        assert result["record"] is not None
        assert result["selected_candidate_index"] == 0
        assert result["selection_summary"]["num_candidates"] == 1
        assert result["selection_summary"]["num_valid_candidates"] == 1


        record = result["record"]
        assert record.source.modality == "generated_text"
        assert record.source.source_file == "synthetic://fake"
        assert record.source.source_uri is not None
        assert "model=gpt-4o-mini" in record.source.source_uri
        assert f"prompt_version={record.generation.prompt_version}" in record.source.source_uri

        assert record.metadata.content_group == "logical_reasoning"
        assert record.metadata.item_type == "causal"
        assert record.metadata.difficulty == "medium"

        assert record.content.stimulus == parsed_payload["stimulus"]
        assert record.content.question_stem == parsed_payload["question"]
        assert len(record.content.answer_choices) == 5
        assert record.content.correct_answer == "A"

        assert record.generation is not None
        assert record.generation.backend == "fake"
        assert record.generation.model == "gpt-4o-mini"
        assert record.generation.flaw_type == "causal"
        assert record.generation.difficulty == "medium"
        assert record.generation.prompt_version is not None

    def test_marks_low_quality_valid_payload_for_review(self, monkeypatch):
        payload = {
            "stimulus": (
                "As an AI, here is your LSAT question. A teacher concludes that online "
                "quizzes improve learning because students who took them scored better "
                "on the final exam."
            ),
            "question": "What do you think about this argument?",
            "answer_choices": [
                {
                    "label": "A",
                    "text": "The students who took online quizzes also attended extra tutoring sessions.",
                },
                {"label": "B", "text": "Some students dislike final exams."},
                {"label": "C", "text": "Tutoring can be expensive."},
                {"label": "D", "text": "Many teachers use online tools."},
                {"label": "E", "text": "Some students prefer shorter quizzes."},
            ],
            "correct_answer": "A",
            "raw_output": "mock raw output",
        }

        monkeypatch.setattr(
            "src.normalize.run_synthetic_lr_lane.generate_synthetic_lr",
            lambda **kwargs: ("mock raw output", _fake_generation_meta(**kwargs)),
        )
        monkeypatch.setattr(
            "src.normalize.run_synthetic_lr_lane.parse_synthetic_lr_output",
            lambda raw: payload,
        )

        result = run_synthetic_lr_lane(persist=False)

        assert result["status"] == "needs_review"
        assert result["stage"] == "synthetic_canonical"
        assert result["record"] is not None
        assert result["content_quality"]["status"] == "review"
        assert "meta_language_detected" in result["content_quality"]["flags"]
        assert "question_not_lsat_style" in result["content_quality"]["flags"]
        assert "synthetic_quality:meta_language_detected" in result["errors"]

    def test_returns_structural_review_result_for_invalid_payload(self, monkeypatch):
        raw_output = """Stimulus: Some argument text.

Question: Which one of the following is flawed?

A. First choice
B. Second choice
C. Third choice

Correct: A
"""

        invalid_payload = {
            "stimulus": "Some argument text.",
            "question": "Which one of the following is flawed?",
            "answer_choices": [
                {"label": "A", "text": "First choice"},
                {"label": "B", "text": "Second choice"},
                {"label": "C", "text": "Third choice"},
            ],
            "correct_answer": "A",
            "raw_output": raw_output,
        }

        monkeypatch.setattr(
            "src.normalize.run_synthetic_lr_lane.generate_synthetic_lr",
            lambda **kwargs: (raw_output, _fake_generation_meta(**kwargs)),
        )
        monkeypatch.setattr(
            "src.normalize.run_synthetic_lr_lane.parse_synthetic_lr_output",
            lambda text: invalid_payload,
        )

        result = run_synthetic_lr_lane()

        assert result["status"] == "needs_review"
        assert result["stage"] == "synthetic_structural"
        assert result["record"] is None
        assert result["content_quality"] is None
        assert result["destination"] == ("review", "synthetic_structural")
        assert result["selected_candidate_index"] is None
        assert result["selection_summary"]["num_candidates"] == 1
        assert result["selection_summary"]["num_valid_candidates"] == 0
        assert result["errors"]
    
    def test_returns_canonical_record_for_sampling_payload(self, monkeypatch):
        raw_output = """Stimulus: A poll of only students in one club found that most prefer later class times, so the university should move all classes later.

Question: Which one of the following most accurately describes a flaw in the argument?

A. It assumes a small, unrepresentative sample is representative of the whole population.
B. It rejects a claim because it is unpopular.
C. It confuses a necessary condition with a sufficient condition.
D. It relies on ambiguous wording.
E. It attacks the character of the students.

Correct: A
"""
        parsed_payload = {
            "stimulus": "A poll of only students in one club found that most prefer later class times, so the university should move all classes later.",
            "question": "Which one of the following most accurately describes a flaw in the argument?",
            "answer_choices": [
                {"label": "A", "text": "It assumes a small, unrepresentative sample is representative of the whole population."},
                {"label": "B", "text": "It rejects a claim because it is unpopular."},
                {"label": "C", "text": "It confuses a necessary condition with a sufficient condition."},
                {"label": "D", "text": "It relies on ambiguous wording."},
                {"label": "E", "text": "It attacks the character of the students."},
            ],
            "correct_answer": "A",
            "raw_output": raw_output,
        }

        monkeypatch.setattr(
            "src.normalize.run_synthetic_lr_lane.generate_synthetic_lr",
            lambda **kwargs: (raw_output, _fake_generation_meta(**kwargs)),

        )
        monkeypatch.setattr(
            "src.normalize.run_synthetic_lr_lane.parse_synthetic_lr_output",
            lambda text: parsed_payload,
        )

        result = run_synthetic_lr_lane(flaw_type="sampling")

        assert result["status"] == "valid"
        assert result["record"] is not None
        assert result["record"].metadata.item_type == "sampling"
        assert result["record"].generation.flaw_type == "sampling"

