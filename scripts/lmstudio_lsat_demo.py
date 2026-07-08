from openai import OpenAI
from pathlib import Path
import csv
from datetime import datetime

# LM Studio local server
client = OpenAI(
    base_url="http://127.0.0.1:1234/v1",
    api_key="lm-studio"
)

LR_QUESTIONS_PATH = Path("data/lsat/lr_questions.csv")
LR_ATTEMPTS_PATH = Path("lr_attempts.csv")
RC_QUESTIONS_PATH = Path("rc_questions.csv")
RC_ATTEMPTS_PATH = Path("rc_attempts.csv")


def load_lr_question(question_id: str):
    """
    Look up a question in lr_questions.csv and load its text slice
    from the referenced file using text_start/text_end.
    Falls back to full file if offsets are missing or invalid.
    """
    with LR_QUESTIONS_PATH.open("r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["question_id"] == question_id:
                text_file = Path(row["text_file"])
                full_text = text_file.read_text()

                # offsets from CSV
                try:
                    start = int(row["text_start"])
                    end = int(row["text_end"])
                except ValueError:
                    start, end = 0, len(full_text)

                # fallback if bad offsets
                if end <= start or end > len(full_text):
                    start, end = 0, len(full_text)

                question_text = full_text[start:end]

                return {
                    "question_id": row["question_id"],
                    "section_index": row["section_index"],
                    "question_type": row["question_type"],
                    "difficulty": row["difficulty"],
                    "skills": row["skills"],
                    "text": question_text,
                    "correct_answer": row["correct_answer"].strip(),
                }

    raise ValueError(f"Question id {question_id} not found in lr_questions.csv")

def load_rc_passage(passage_id: str):
    """
    Look up one RC question belonging to a passage in rc_questions.csv and
    load its text slice from the referenced file using text_start/text_end.
    For now, this returns the first question it finds for that passage and
    the text slice for that question only (we'll extend to full passage later).
    """
    with RC_QUESTIONS_PATH.open("r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["passage_id"] == passage_id:
                text_file = Path(row["text_file"])
                full_text = text_file.read_text()

                try:
                    start = int(row["text_start"])
                    end = int(row["text_end"])
                except ValueError:
                    start, end = 0, len(full_text)

                if end <= start or end > len(full_text):
                    start, end = 0, len(full_text)

                question_text = full_text[start:end]

                return {
                    "passage_id": row["passage_id"],
                    "question_id": row["question_id"],
                    "question_type": row["question_type"],
                    "difficulty": row["difficulty"],
                    "skills": row["skills"],
                    "text": question_text,
                    "correct_answer": row["correct_answer"].strip(),
                    "text_file": row["text_file"],
                    "text_start": start,
                    "text_end": end,
                }

    raise ValueError(f"Passage id {passage_id} not found in rc_questions.csv")


def ensure_attempts_header():
    if not LR_ATTEMPTS_PATH.exists():
        with LR_ATTEMPTS_PATH.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp",
                "question_id",
                "student_answer",
                "correct_answer",
                "is_correct",
                "model_verdict_short",
            ])


def main():
    # 1. Load question metadata + text
    q = load_lr_question("demo_lr_1")
    print(f"Question ID: {q['question_id']} (section {q['section_index']})\n")
    print(q["text"])
    print()

    # 2. Ask you for your answer
    student_answer = input("Your answer (A/B/C/D/E): ").strip().upper()
    correct_answer = q["correct_answer"]
    is_correct = student_answer == correct_answer

    # 3. Build prompt for LM Studio
    prompt = f"""
You are an expert LSAT Logical Reasoning tutor.

Question ID: {q['question_id']}

Question and choices:
{q["text"]}

Student's answer: {student_answer}
Correct answer:   {correct_answer}

Task:
1. Identify the conclusion and the key premises.
2. Name the question type if possible.
3. Explain the main flaw or reasoning task.
4. Evaluate each choice briefly.
5. At the end, give a SHORT verdict line starting with 'Verdict:' that says whether the student is correct and why in 1–2 sentences.
"""

    resp = client.chat.completions.create(
        model="llama-3-8b-lexi-uncensored",
        messages=[
            {
                "role": "system",
                "content": "You are an expert LSAT tutor. Be concise but precise."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.3,
        max_tokens=500,
    )

    full_answer = resp.choices[0].message.content
    print("\n--- Tutor response ---\n")
    print(full_answer)

    # 4. Extract verdict line
    verdict_line = ""
    for line in full_answer.splitlines()[::-1]:
        if line.strip().lower().startswith("verdict:"):
            verdict_line = line.strip()
            break

    # 5. Append attempt to lr_attempts.csv
    ensure_attempts_header()
    with LR_ATTEMPTS_PATH.open("a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().isoformat(timespec="seconds"),
            q["question_id"],
            student_answer,
            correct_answer,
            "1" if is_correct else "0",
            verdict_line,
        ])

    print("\nAttempt logged to lr_attempts.csv")


if __name__ == "__main__":
    main()
