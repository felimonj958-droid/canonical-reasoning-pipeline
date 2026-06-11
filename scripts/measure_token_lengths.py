from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List

from src.classify.chunking import (
    build_classification_text,
    count_tokens,
    load_tokenizer,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RECORDS_DIR = PROJECT_ROOT / "data" / "normalized" / "records"


def iter_record_files(records_dir: Path):
    for path in sorted(records_dir.rglob("*.json")):
        yield path


def percentile(values: List[int], pct: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    if len(values) == 1:
        return float(values[0])

    rank = (len(values) - 1) * pct
    low = int(rank)
    high = min(low + 1, len(values) - 1)
    weight = rank - low
    return values[low] * (1 - weight) + values[high] * weight


def summarize_thresholds(values: List[int]) -> Dict[str, Any]:
    thresholds = [128, 256, 384, 512, 768, 1024, 2048, 4096]
    total = len(values)

    if total == 0:
        return {"total": 0, "thresholds": {}}

    summary = {}
    for threshold in thresholds:
        count = sum(v <= threshold for v in values)
        summary[str(threshold)] = {
            "count": count,
            "pct": round((count / total) * 100, 2),
        }

    return {"total": total, "thresholds": summary}


def detect_has_late_evidence(text: str, window_chars: int = 1200) -> bool:
    if not text:
        return False

    late_slice = text[window_chars:].lower()
    markers = [
        "answer choices",
        "choice a",
        "(a)",
        "explanation",
        "because",
        "therefore",
    ]
    return any(marker in late_slice for marker in markers)


def main():
    tokenizer = load_tokenizer()
    rows: List[Dict[str, Any]] = []

    for path in iter_record_files(RECORDS_DIR):
        with open(path, "r", encoding="utf-8") as f:
            record = json.load(f)

        text = build_classification_text(record)
        token_count = count_tokens(text, tokenizer)

        rows.append(
            {
                "path": str(path.relative_to(PROJECT_ROOT)),
                "source_id": record.get("source_id"),
                "document_type": record.get("document_type", "unknown"),
                "section_type": record.get("section_type", "unknown"),
                "token_count": token_count,
                "has_late_evidence": detect_has_late_evidence(text),
            }
        )

    token_counts = [row["token_count"] for row in rows]
    late_evidence_count = sum(1 for row in rows if row["has_late_evidence"])

    print("\nTOKEN LENGTH REPORT")
    print("=" * 60)
    print(f"records: {len(rows)}")
    print(f"mean_tokens: {round(mean(token_counts), 2) if token_counts else 0}")
    print(f"p50_tokens: {round(percentile(token_counts, 0.50), 2) if token_counts else 0}")
    print(f"p90_tokens: {round(percentile(token_counts, 0.90), 2) if token_counts else 0}")
    print(f"p95_tokens: {round(percentile(token_counts, 0.95), 2) if token_counts else 0}")
    print(f"max_tokens: {max(token_counts) if token_counts else 0}")
    print(f"late_evidence_records: {late_evidence_count}")

    threshold_summary = summarize_thresholds(token_counts)
    print("\nTHRESHOLDS")
    for threshold, stats in threshold_summary.get("thresholds", {}).items():
        print(f"<= {threshold}: {stats['count']} records ({stats['pct']}%)")

    by_doc_type: Dict[str, List[int]] = {}
    for row in rows:
        by_doc_type.setdefault(row["document_type"], []).append(row["token_count"])

    print("\nBY DOCUMENT TYPE")
    for doc_type, values in sorted(by_doc_type.items()):
        print(
            f"{doc_type}: n={len(values)}, "
            f"mean={round(mean(values), 2)}, "
            f"p90={round(percentile(values, 0.90), 2)}, "
            f"max={max(values)}"
        )


if __name__ == "__main__":
    main()
