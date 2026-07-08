from openai import OpenAI
from pathlib import Path
import csv

# Reuse the same CSV and model setup
LR_QUESTIONS_PATH = Path("data/lsat/lr_questions.csv")

client = OpenAI(
    base_url="http://127.0.0.1:1234/v1",
    api_key="lm-studio"
)


def load_lr_text(question_id: str) -> str:
    """Return raw text slice for a given LR question id."""
    with LR_QUESTIONS_PATH.open("r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["question_id"] == question_id:
                text_file = Path(row["text_file"])
                full_text = text_file.read_text()

                try:
                    start = int(row["text_start"])
                    end = int(row["text_end"])
                except ValueError:
                    start, end = 0, len(full_text)

                if end <= start or end > len(full_text):
                    start, end = 0, len(full_text)

                return full_text[start:end]

    raise ValueError(f"Question id {question_id} not found in lr_questions.csv")


def main():
    question_id = "demo_lr_1"

    text = load_lr_text(question_id)
    print(f"Loaded text for {question_id}:\n")
    print(text)
    print("\n--- Asking model to auto-label ---\n")

    prompt = f"""
You are an expert LSAT Logical Reasoning instructor.

Below is one complete LSAT-style Logical Reasoning question (stimulus + choices).

Question:
{text}

Your task: analyze this question and output a SINGLE JSON object on one line
with the following keys:

- "question_type": a short label like "Assumption-necessary", "Flaw",
  "Strengthen", "Weaken", "Inference", "Parallel", etc.
- "difficulty": an integer from 1 to 5 (1 = very easy, 5 = very hard).
- "skills": a list of 1-3 short skill tags, like
  ["conditional_logic", "causal", "inference", "principle"].

Important:
- Respond ONLY with JSON. No explanations, no extra text.
- Use double quotes for all JSON keys and string values.

Example format (the content is just an example):

{{"question_type": "Flaw", "difficulty": 3, "skills": ["causal", "inference"]}}
"""

    resp = client.chat.completions.create(
        model="llama-3-8b-lexi-uncensored",
        messages=[
            {
                "role": "system",
                "content": "You are an expert LSAT tutor and labeling assistant."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.1,
        max_tokens=200,
    )

    json_line = resp.choices[0].message.content.strip()
    print("Suggested JSON label:")
    print(json_line)


if __name__ == "__main__":
    main()
