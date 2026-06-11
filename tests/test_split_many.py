from pathlib import Path

from src.normalize.clean_text import normalize
from src.normalize.split_lsat import split_many_lsat_questions


def test_split_many_lsat_questions_page_text():
    raw = Path("data/pt62/lr2/pt62_lr2_p01.txt").read_text(encoding="utf-8")
    cleaned = normalize(raw)

    chunks = split_many_lsat_questions(cleaned)

    assert len(chunks) >= 2
    assert any("Which one of the following" in chunk for chunk in chunks)

