from src.classify.chunking import (
    build_classification_text,
    choose_strategy,
    chunk_text,
    count_tokens,
    prepare_classification_payload,
)


class FakeTokenizer:
    def encode(self, text, add_special_tokens=True):
        tokens = text.split()
        if add_special_tokens:
            return ["[CLS]"] + tokens + ["[SEP]"]
        return tokens

    def __call__(
        self,
        text,
        add_special_tokens=False,
        return_offsets_mapping=True,
        truncation=False,
    ):
        words = text.split()
        input_ids = list(range(len(words)))
        offsets = []

        cursor = 0
        for word in words:
            start = text.index(word, cursor)
            end = start + len(word)
            offsets.append((start, end))
            cursor = end

        return {"input_ids": input_ids, "offset_mapping": offsets}


def test_build_classification_text_includes_nested_lsat_fields():
    record = {
        "record_id": "lr-001",
        "source": {
            "modality": "generated_text",
            "source_file": "data/raw_text/sample.txt",
        },
        "lsat": {
            "exam": "LSAT",
            "prep_test": "PT62",
            "section": "logical_reasoning",
            "section_number": 2,
            "question_number": 1,
        },
        "content": {
            "question_stem": "Which one of the following is most strongly supported?",
            "answer_choices": [
                {"label": "A", "text": "Red"},
                {"label": "B", "text": "Blue"},
            ],
            "normalized_text": "Which one of the following is most strongly supported? (A) Red (B) Blue",
        },
    }

    text = build_classification_text(record)

    assert "record_id: lr-001" in text
    assert "prep_test: PT62" in text
    assert "section: logical_reasoning" in text
    assert "question_stem: Which one of the following is most strongly supported?" in text
    assert "answer_choices: A. Red | B. Blue" in text
    assert "full_text:" in text


def test_count_tokens_returns_nonzero_for_text():
    tokenizer = FakeTokenizer()
    text = "This is a short LSAT question."

    count = count_tokens(text, tokenizer)

    assert count > 0


def test_choose_strategy_returns_single_window_for_short_text():
    result = choose_strategy(token_count=120)

    assert result["strategy"] == "single_window"
    assert result["near_limit"] is False


def test_choose_strategy_returns_chunked_for_long_text():
    result = choose_strategy(token_count=900)

    assert result["strategy"] == "chunked"


def test_choose_strategy_returns_hierarchical_when_late_evidence_present():
    result = choose_strategy(token_count=900, has_late_evidence=True)

    assert result["strategy"] == "chunked_hierarchical"


def test_chunk_text_splits_long_text_into_multiple_chunks():
    tokenizer = FakeTokenizer()
    text = " ".join(f"token{i}" for i in range(100))

    chunks = chunk_text(text, tokenizer, max_tokens=20, overlap_tokens=5)

    assert len(chunks) > 1
    assert chunks[0]["chunk_index"] == 0
    assert chunks[1]["token_start"] < chunks[1]["token_end"]


def test_prepare_classification_payload_uses_chunking_for_long_nested_record():
    tokenizer = FakeTokenizer()
    record = {
        "record_id": "rc-001",
        "source": {
            "modality": "generated_text",
            "source_file": "data/raw_text/sample.txt",
        },
        "lsat": {
            "exam": "LSAT",
            "prep_test": "DEMO",
            "section": "reading_comprehension",
            "section_number": 1,
            "question_number": 1,
        },
        "content": {
            "question_stem": "Which one of the following is best supported?",
            "answer_choices": [
                {"label": "A", "text": "choice a"},
                {"label": "B", "text": "choice b"},
            ],
            "normalized_text": " ".join(f"token{i}" for i in range(800)),
        },
    }

    payload = prepare_classification_payload(
        record,
        tokenizer=tokenizer,
        max_tokens=50,
        overlap_tokens=10,
        soft_limit_tokens=60,
    )

    assert payload["strategy"] == "chunked"
    assert len(payload["chunks"]) > 1
