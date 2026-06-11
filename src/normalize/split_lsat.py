import re


def _extract_choices(cleaned_text):
    lines = cleaned_text.split("\n")
    choices = []
    current_label = None
    current_text_lines = []

    for line in lines:
        line_stripped = line.lstrip()
        if line_stripped.startswith("(") and len(line_stripped) >= 3 and line_stripped[2] == ")":
            # New choice starting
            if current_label is not None:
                choices.append(
                    {
                        "label": current_label,
                        "text": " ".join(current_text_lines).strip(),
                    }
                )

            current_label = line_stripped[1]
            current_text_lines = [line_stripped[3:].strip()]
        else:
            if current_label is not None:
                current_text_lines.append(line.strip())

    if current_label is not None:
        choices.append(
            {
                "label": current_label,
                "text": " ".join(current_text_lines).strip(),
            }
        )

    return choices


def split(cleaned_text, hints=None):
    hints = hints or {}
    cleaned_text = cleaned_text.strip()

    lines = cleaned_text.split("\n")
    choice_start_idx = None
    for idx, line in enumerate(lines):
        if line.lstrip().startswith("(") and len(line.lstrip()) >= 3 and line.lstrip()[2] == ")":
            choice_start_idx = idx
            break

    if choice_start_idx is None:
        question_block_lines = lines
        choice_block_text = ""
    else:
        question_block_lines = lines[:choice_start_idx]
        choice_block_text = "\n".join(lines[choice_start_idx:])

    answer_choices = _extract_choices(choice_block_text)

    question_block = "\n".join(question_block_lines).strip()
    paragraphs = [p.strip() for p in question_block.split("\n\n") if p.strip()]

    stimulus = None
    question_stem = None
    passage = None

    if hints.get("section") == "reading_comprehension":
        if len(paragraphs) >= 2:
            passage = "\n\n".join(paragraphs[:-1]).strip()
            question_stem = paragraphs[-1].strip()
        elif paragraphs:
            passage = paragraphs[0]
    else:
        if len(paragraphs) >= 2:
            stimulus = "\n\n".join(paragraphs[:-1]).strip()
            question_stem = paragraphs[-1].strip()
        elif paragraphs:
            question_stem = paragraphs[0].strip()

    return {
        "passage": passage,
        "stimulus": stimulus,
        "question_stem": question_stem,
        "answer_choices": answer_choices,
        "correct_answer": hints.get("correct_answer"),
        "explanation": None,
    }

def split_many_lsat_questions(cleaned_text):
    pattern = re.compile(r'(?m)^\s*(\d{1,2})[.,]?\s+')
    matches = list(pattern.finditer(cleaned_text))

    if not matches:
        return [cleaned_text.strip()] if cleaned_text.strip() else []

    chunks = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(cleaned_text)
        chunk = cleaned_text[start:end].strip()
        if chunk:
            chunks.append(chunk)

    return chunks

