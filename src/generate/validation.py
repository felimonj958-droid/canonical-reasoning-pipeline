def validate_synthetic_lr_payload(payload: dict) -> dict:
    errors = []

    stimulus = payload.get("stimulus", "").strip()
    question = payload.get("question", "").strip()
    choices = payload.get("answer_choices", [])
    correct = payload.get("correct_answer", "").strip().upper()

    if not stimulus:
        errors.append("missing_stimulus")

    if not question:
        errors.append("missing_question")

    if len(choices) != 5:
        errors.append("invalid_choice_count")

    labels = [c.get("label", "").strip().upper() for c in choices]
    if set(labels) != {"A", "B", "C", "D", "E"}:
        errors.append("invalid_choice_labels")

    texts = [c.get("text", "").strip() for c in choices]
    if any(not t for t in texts):
        errors.append("empty_choice_text")

    normalized_texts = [t.casefold() for t in texts if t]
    if len(set(normalized_texts)) != len(normalized_texts):
        errors.append("duplicate_choice_text")

    if not correct:
        errors.append("missing_correct_answer")
    elif correct not in {"A", "B", "C", "D", "E"}:
        errors.append("invalid_correct_answer_label")



    return {
        "status": "valid" if not errors else "needs_review",
        "errors": errors,
    }
