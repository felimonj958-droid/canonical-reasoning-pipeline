from src.ocr.extract_text import extract_text_from_stub


def run_ocr(manifest, config=None):
    config = config or {}

    # For Session 2 MVP, always use the stub that reads paired text.
    ocr_result = extract_text_from_stub(manifest)

    return ocr_result

