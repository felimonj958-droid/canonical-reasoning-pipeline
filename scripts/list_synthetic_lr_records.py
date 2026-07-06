from __future__ import annotations

import json
from pathlib import Path
from textwrap import shorten


def list_synthetic_lr_records(
    normalized_root: Path = Path("data/normalized/records"),
    max_records: int | None = None,
) -> None:
    if not normalized_root.exists():
        print(f"[!] Normalized root does not exist: {normalized_root}")
        return

    json_files = sorted(
        normalized_root.glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    count = 0

    print(
        "record_id\tflaw_type\tdifficulty\tcreated_at\tstimulus_snippet"
    )

    for path in json_files:
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            print(f"[!] Failed to read {path}: {exc}")
            continue

        source = data.get("source") or {}
        lsat = data.get("lsat") or {}
        content = data.get("content") or {}

        source_uri = source.get("source_uri") or ""
        if "synthetic://ollama" not in source_uri:
            continue

        record_id = data.get("record_id", path.stem)
        flaw_type = lsat.get("question_type") or "-"
        difficulty = lsat.get("difficulty") or "-"
        created_at = source.get("created_at") or "-"

        stimulus = content.get("stimulus") or ""
        snippet = shorten(stimulus.replace("\n", " "), width=80, placeholder="…")

        print(
            f"{record_id}\t{flaw_type}\t{difficulty}\t{created_at}\t{snippet}"
        )

        count += 1
        if max_records is not None and count >= max_records:
            break

    if count == 0:
        print("[i] No synthetic Ollama-based LR records found.")


if __name__ == "__main__":
    list_synthetic_lr_records()
