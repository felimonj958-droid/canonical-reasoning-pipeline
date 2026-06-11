from src.ingest.image_loader import load_image
from src.ocr.ocr_router import run_ocr
from src.normalize.clean_text import normalize
from src.normalize.split_lsat import split
from src.normalize.canonical_mapper import map_to_record
from src.persist.filesystem_store import save_record
from src.validate.confidence_checks import validate_record
from src.validate.review_routing import choose_destination


def run_image_lane(image_path, metadata=None):
    metadata = metadata or {}

    manifest = load_image(image_path, metadata)

    ocr_result = run_ocr(manifest, {})
    raw_text = ocr_result["text"]

    cleaned = normalize(raw_text)
    segments = split(cleaned, {"section": metadata.get("section")})
    record = map_to_record(
        manifest,
        raw_text,
        cleaned,
        segments,
        ocr=None,
        image_quality=None,
    )

    record = validate_record(record)
    destination, review_reason = choose_destination(record)

    out_path = save_record(
        record,
        destination=destination,
        review_reason=review_reason,
    )

    review_path = out_path if destination == "review" else None

    return record, out_path, review_path
