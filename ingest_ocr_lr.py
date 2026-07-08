from pathlib import Path
import csv
import sys
import re

LR_QUESTIONS_PATH = Path("data/lsat/lr_questions.csv")


def load_existing_ids():
    """Return a set of question_ids already in lr_questions.csv."""
    ids = set()
    if LR_QUESTIONS_PATH.exists():
        with LR_QUESTIONS_PATH.open("r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ids.add(row["question_id"])
    return ids


def ensure_header():
    if not LR_QUESTIONS_PATH.exists():
        with LR_QUESTIONS_PATH.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "question_id",
                "section_index",
                "question_type",
                "difficulty",
                "skills",
                "text_file",
                "text_start",
                "text_end",
                "correct_answer",
            ])


def split_questions(raw_text: str):
    """
    Split OCR text into Logical Reasoning question blocks.

    We treat each block that contains answer choices (A)–(E) as one question.
    Returns list of (block_text, start_index, end_index) in the original string.
    """
    blocks = []

    # Pattern: from some text up to and including choices (A) ... (E),
    # as they appear in order. DOTALL so it spans multiple lines.
    choice_pattern = re.compile(
        r"(.*?\(A\).*?\(B\).*?\(C\).*?\(D\).*?\(E\).*?)",
        re.DOTALL
    )

    for match in choice_pattern.finditer(raw_text):
        start = match.start(1)
        end = match.end(1)
        block_text = raw_text[start:end].strip()
        if block_text:
            blocks.append((block_text, start, end))

    return blocks


def main():
    if len(sys.argv) < 3:
        print("Usage: python ingest_ocr_lr.py <text_file> <section_index>")
        print("Example: python ingest_ocr_lr.py pt52_lr.txt 1")
        sys.exit(1)

    text_file = Path(sys.argv[1])
    section_index = sys.argv[2]

    if not text_file.exists():
        print(f"Text file {text_file} not found.")
        sys.exit(1)

    raw_text = text_file.read_text()
    blocks = split_questions(raw_text)

    print(f"Found {len(blocks)} question blocks in {text_file.name}")

    ensure_header()
    existing_ids = load_existing_ids()

    with LR_QUESTIONS_PATH.open("a", newline="") as f:
        writer = csv.writer(f)
        for idx, (block_text, start, end) in enumerate(blocks, start=1):
            question_id = f"{text_file.stem}_Q{idx:02d}"
            if question_id in existing_ids:
                print(f"Skipping existing question_id {question_id}")
                continue

            writer.writerow([
                question_id,
                section_index,
                "",             # question_type
                "",             # difficulty
                "",             # skills
                text_file.name,
                start,
                end,
                "",             # correct_answer
            ])
            print(f"Added {question_id} (chars {start}-{end})")

    print("Done. Rows appended to lr_questions.csv.")


if __name__ == "__main__":
    main()
