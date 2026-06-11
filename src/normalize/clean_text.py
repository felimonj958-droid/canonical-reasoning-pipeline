import re


def normalize(text):
    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")

    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("‘", "'").replace("’", "'")
    text = text.replace("—", "-").replace("–", "-")

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Normalize answer labels without double-wrapping already-correct labels.
    text = re.sub(r"\\(\\s\*([A-E])\\s\*\\)", r"(\1)", text)
    text = re.sub(r"(?m)^([A-E])\)", r"(\1)", text)

    text = re.sub(r"(?m)^\s+", "", text)
    text = re.sub(r"(?m)\s+$", "", text)

    return text.strip()

