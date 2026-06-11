from src.ingest.text_loader import load_text
from src.normalize.clean_text import normalize
from src.normalize.split_lsat import split
from src.normalize.canonical_mapper import map_to_record
from src.persist.filesystem_store import save_record
from src.validate.confidence_checks import validate_record
from src.validate.review_routing import choose_destination


def run_text_lane(text_path, metadata=None):
    metadata = metadata or {}

    manifest, raw_text = load_text(text_path, metadata)
    cleaned = normalize(raw_text)
    segments = split(cleaned, {"section": metadata.get("section")})
    record = map_to_record(manifest, raw_text, cleaned, segments)

    record = validate_record(record)
    destination, review_reason = choose_destination(record)

    out_path = save_record(
        record,
        destination=destination,
        review_reason=review_reason,
    )

    review_path = out_path if destination == "review" else None

    return record, out_path, review_path
