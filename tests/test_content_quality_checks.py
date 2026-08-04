from src.generate.content_quality_checks import (
    check_question_style,
    run_content_quality_checks,
)


class TestQuestionStyle:
    def test_accepts_vulnerable_to_criticism_stem(self):
        stem = "The reasoning in the argument is most vulnerable to criticism on the grounds that it"
        flags = check_question_style(stem)
        assert flags == []

    def test_accepts_flaw_describes_stem(self):
        stem = "Which one of the following most accurately describes a flaw in the argument?"
        flags = check_question_style(stem)
        assert flags == []

    def test_flags_non_lsat_stem(self):
        stem = "How do you feel about this argument?"
        flags = check_question_style(stem)
        assert flags == ["question_not_lsat_style"]


class TestRunContentQualityChecks:
    def test_flags_meta_language_and_routes_to_review(self):
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
        }

        result = run_content_quality_checks(payload)

        assert result.status == "review"
        assert "meta_language_detected" in result.flags
        assert "question_not_lsat_style" in result.flags

def test_content_quality_passes_reasonable_lr_item():
    payload = {
        "stimulus": (
            "A city council member argues that the new bike-lane program should be "
            "expanded. Since the neighborhoods that received bike lanes last year "
            "saw an increase in local retail activity, the council member concludes "
            "that adding more bike lanes will probably improve business activity in "
            "other neighborhoods as well."
        ),
        "question": (
            "Which one of the following most accurately describes a flaw in the "
            "council member's reasoning?"
        ),
        "answer_choices": [
            {"label": "A", "text": "It treats a correlation as though it established a causal relationship."},
            {"label": "B", "text": "It fails to consider that some retail stores may prefer fewer customers."},
            {"label": "C", "text": "It assumes that all neighborhoods have identical zoning laws."},
            {"label": "D", "text": "It overlooks the possibility that bike lanes are legally required in all cities."},
            {"label": "E", "text": "It confuses a sufficient condition for a necessary one."},
        ],
        "correct_answer": "A",
    }

    result = run_content_quality_checks(payload)

    assert result.status == "pass"
    assert result.score >= 0.70
    assert "meta_language_detected" not in result.flags
    assert "question_not_lsat_style" not in result.flags


def test_content_quality_flags_meta_language():
    payload = {
        "stimulus": (
            "As an AI, here is your LSAT stimulus. A recent survey showed that "
            "students who used flashcards scored higher on a logic exam."
        ),
        "question": "Which one of the following weakens the argument?",
        "answer_choices": [
            {"label": "A", "text": "Many students who used flashcards also studied longer overall."},
            {"label": "B", "text": "Some students dislike standardized tests."},
            {"label": "C", "text": "Logic exams are often difficult."},
            {"label": "D", "text": "Flashcards are sold in many bookstores."},
            {"label": "E", "text": "Some students have good memories."},
        ],
        "correct_answer": "A",
    }

    result = run_content_quality_checks(payload)

    assert result.status == "review"
    assert "meta_language_detected" in result.flags


def test_content_quality_flags_non_lsat_question_style():
    payload = {
        "stimulus": (
            "A restaurant owner concludes that a new menu caused higher profits "
            "because profits rose after the menu changed."
        ),
        "question": "What do you think about this argument?",
        "answer_choices": [
            {"label": "A", "text": "It assumes a causal relationship from a mere sequence of events."},
            {"label": "B", "text": "It proves that menus never affect profit."},
            {"label": "C", "text": "It shows that customers dislike restaurants."},
            {"label": "D", "text": "It demonstrates that profits are irrelevant."},
            {"label": "E", "text": "It establishes that all business changes are risky."},
        ],
        "correct_answer": "A",
    }

    result = run_content_quality_checks(payload)

    assert "question_not_lsat_style" in result.flags


def test_content_quality_flags_choice_length_imbalance():
    payload = {
        "stimulus": (
            "A columnist argues that because one town reduced traffic after adding "
            "a roundabout, every town can reduce traffic by adding roundabouts."
        ),
        "question": (
            "Which one of the following most accurately describes a flaw in the "
            "columnist's reasoning?"
        ),
        "answer_choices": [
            {"label": "A", "text": "Overgeneralizes."},
            {"label": "B", "text": "It generalizes from a single example to all towns without showing that the relevant conditions are similar across cases."},
            {"label": "C", "text": "No."},
            {"label": "D", "text": "Maybe."},
            {"label": "E", "text": "Possibly."},
        ],
        "correct_answer": "B",
    }

    result = run_content_quality_checks(payload)

    assert "choice_length_imbalance" in result.flags or "choice_too_short" in result.flags


def test_content_quality_flags_duplicate_choices():
    payload = {
        "stimulus": (
            "A teacher concludes that online quizzes improve learning because "
            "students who took them scored better on the final exam."
        ),
        "question": (
            "Which one of the following most weakens the teacher's argument?"
        ),
        "answer_choices": [
            {"label": "A", "text": "The students who took online quizzes also attended extra tutoring sessions."},
            {"label": "B", "text": "The students who took online quizzes also attended extra tutoring sessions."},
            {"label": "C", "text": "Some students dislike final exams."},
            {"label": "D", "text": "Tutoring can be expensive."},
            {"label": "E", "text": "Many teachers use online tools."},
        ],
        "correct_answer": "A",
    }

    result = run_content_quality_checks(payload)

    assert "near_duplicate_choices" in result.flags
    assert result.status == "review"
