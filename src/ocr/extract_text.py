from pathlib import Path


def _guess_paired_text_path(source_file):
    image_path = Path(source_file)
    stem = image_path.stem

    candidates = [
        Path("data/pt62/lr2") / f"{stem}.txt",
        Path("data/pt62/lr2") / f"{stem.replace('.jpeg', '')}.txt",
        Path("data/pt62/lr2") / f"{stem.replace('_clean', '_clean')}.txt",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(f"No paired OCR text found for image: {source_file}")


def extract_text_from_stub(manifest):
    text_path = _guess_paired_text_path(manifest.source_file)
    text = text_path.read_text(encoding="utf-8")

    return {
        "text": text,
        "text_path": str(text_path),
        "mean_confidence": None,
        "min_line_confidence": None,
        "low_confidence_spans": [],
    }

