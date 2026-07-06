from src.generate.validation import validate_synthetic_lr_payload


def test_validate_synthetic_lr_payload_happy_path():
    payload = {
        "stimulus": "A study found that coffee drinkers are more likely to have heart disease. Therefore, coffee causes heart disease.",
        "question": "Which answer choice best describes the flaw in the reasoning?",
        "answer_choices": [
            {"label": "A", "text": "The argument overlooks possible confounding variables."},
            {"label": "B", "text": "The argument assumes a causal relationship from a correlation."},
            {"label": "C", "text": "The argument relies on an unrepresentative sample."},
            {"label": "D", "text": "The argument confuses sufficient and necessary conditions."},
            {"label": "E", "text": "The argument attacks the character of coffee drinkers."},
        ],
        "correct_answer": "B",
    }

    result = validate_synthetic_lr_payload(payload)

    assert result["status"] == "valid"
    assert result["errors"] == []


def test_validate_synthetic_lr_payload_detects_bad_count_and_labels():
    payload = {
        "stimulus": "Some argument.",
        "question": "Which choice best describes the flaw?",
        "answer_choices": [
            {"label": "A", "text": "Choice one"},
            {"label": "B", "text": "Choice two"},
            {"label": "C", "text": "Choice three"},
        ],
        "correct_answer": "D",
    }

    result = validate_synthetic_lr_payload(payload)

    assert result["status"] == "needs_review"
    assert "invalid_choice_count" in result["errors"]
    assert "invalid_choice_labels" in result["errors"]


def test_validate_synthetic_lr_payload_detects_duplicate_choice_text():
    payload = {
        "stimulus": "Some argument.",
        "question": "Which choice best describes the flaw?",
        "answer_choices": [
            {"label": "A", "text": "Same text"},
            {"label": "B", "text": "Same text"},
            {"label": "C", "text": "Different text"},
            {"label": "D", "text": "Another text"},
            {"label": "E", "text": "Last text"},
        ],
        "correct_answer": "C",
    }

    result = validate_synthetic_lr_payload(payload)

    assert result["status"] == "needs_review"
    assert "duplicate_choice_text" in result["errors"]
