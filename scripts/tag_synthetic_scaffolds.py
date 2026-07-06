from __future__ import annotations

import json
from pathlib import Path


def tag_scaffold_records(
    normalized_root: Path = Path("data/normalized/records"),
    scaffold_stimulus: str = "A simple argument.",
) -> int:
    if not normalized_root.exists():
        print(f"[!] Normalized root does not exist: {normalized_root}")
        return 0

    updated = 0

    for path in normalized_root.glob("*.json"):
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            print(f"[!] Failed to read {path}: {exc}")
            continue

        source = data.get("source") or {}
        lsat = data.get("lsat") or {}
        content = data.get("content") or {}

        # Only touch synthetic Ollama records
        source_uri = source.get("source_uri") or ""
        if "synthetic://ollama" not in source_uri:
            continue

        stimulus = (content.get("stimulus") or "").strip()
        if stimulus != scaffold_stimulus:
            continue

        # Tag as scaffold — in lsat or source; choose one and be consistent
        if lsat.get("prep_test") != "SCAFFOLD":
            lsat["prep_test"] = "SCAFFOLD"
            data["lsat"] = lsat
            updated += 1

            with path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    return updated


if __name__ == "__main__":
    root = Path("data/normalized/records")
    count = tag_scaffold_records(root)
    print(f"[i] Tagged {count} scaffold records in {root}")
