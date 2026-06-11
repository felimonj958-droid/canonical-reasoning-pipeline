from pathlib import Path
from src.ingest.manifest import IngestionManifest


def _infer_modality(path, metadata):
    if "modality" in metadata and metadata["modality"] in {"digital_text", "generated_text"}:
        return metadata["modality"]

    name = path.name.lower()
    if "demo" in name or "generated" in name or metadata.get("source") == "synthetic_generation":
        return "generated_text"

    return "digital_text"


def load_text(text_path, metadata=None):
    metadata = metadata or {}
    path = Path(text_path)

    if not path.exists():
        raise FileNotFoundError(f"Text file not found: {text_path}")

    raw_text = path.read_text(encoding="utf-8")

    manifest = IngestionManifest.from_path(
        path=path,
        modality=_infer_modality(path, metadata),
        prep_test=metadata.get("prep_test"),
        section=metadata.get("section"),
        section_number=metadata.get("section_number"),
        question_number=metadata.get("question_number"),
        page_ref=metadata.get("page_ref"),
        capture_device=metadata.get("capture_device"),
        ocr_engine="none",
    )

    return manifest, raw_text

