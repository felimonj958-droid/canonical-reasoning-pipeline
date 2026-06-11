from pathlib import Path

from src.ingest.manifest import IngestionManifest


def load_image(image_path, metadata=None):
    metadata = metadata or {}
    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    manifest = IngestionManifest.from_path(
        path=path,
        modality="image",
        prep_test=metadata.get("prep_test"),
        section=metadata.get("section"),
        section_number=metadata.get("section_number"),
        question_number=metadata.get("question_number"),
        page_ref=metadata.get("page_ref"),
        capture_device=metadata.get("capture_device", "iPhone"),
        ocr_engine=metadata.get("ocr_engine"),
    )

    return manifest

