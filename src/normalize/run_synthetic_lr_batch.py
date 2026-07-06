from __future__ import annotations

from collections import Counter

from src.llm_client import get_llm_client
from src.normalize.run_synthetic_lr_lane import run_synthetic_lr_lane


def run_synthetic_lr_batch(
    n_per_config: int = 2,
    persist: bool = True,
    model: str | None = None,
) -> dict:
    """Run a small sweep across flaw types and difficulties.

    Uses the LLM_BACKEND env var (default: ollama) via get_llm_client().
    """
    client = get_llm_client()

    configs = [
        ("causal", "easy"),
        ("causal", "medium"),
        ("necessary_vs_sufficient", "easy"),
        ("necessary_vs_sufficient", "medium"),
    ]

    destination_counts: Counter = Counter()
    status_counts: Counter = Counter()
    quality_status_counts: Counter = Counter()
    quality_flag_counts: Counter = Counter()
    runtime_error_counts: Counter = Counter()
    backend_counts: Counter = Counter()

    results = []

    for flaw_type, difficulty in configs:
        for _ in range(n_per_config):
            try:
                out = run_synthetic_lr_lane(
                    flaw_type=flaw_type,
                    difficulty=difficulty,
                    client=client,
                    model=model,
                    persist=persist,
                )
            except Exception as exc:
                error_name = type(exc).__name__
                runtime_error_counts[error_name] += 1

                out = {
                    "status": "needs_review",
                    "destination": ("review", "generation_runtime_error"),
                    "content_quality": None,
                    "saved_path": None,
                    "error": str(exc),
                }

            status_counts[out["status"]] += 1
            dest = out["destination"]
            destination_counts[dest] += 1
            backend_counts[getattr(client, "backend_name", "unknown")] += 1

            cq = out.get("content_quality") or {}
            q_status = cq.get("status")
            if q_status:
                quality_status_counts[q_status] += 1
            for flag in cq.get("flags") or []:
                quality_flag_counts[flag] += 1

            results.append(
                {
                    "flaw_type": flaw_type,
                    "difficulty": difficulty,
                    "status": out["status"],
                    "destination": dest,
                    "quality_status": q_status,
                    "quality_flags": list(cq.get("flags") or []),
                    "saved_path": out.get("saved_path"),
                    "error": out.get("error"),
                }
            )

    summary = {
        "status_counts": dict(status_counts),
        "destination_counts": {str(k): v for k, v in destination_counts.items()},
        "quality_status_counts": dict(quality_status_counts),
        "quality_flag_counts": dict(quality_flag_counts),
        "runtime_error_counts": dict(runtime_error_counts),
        "backend_counts": dict(backend_counts),
        "total_items": len(results),
    }

    return {
        "summary": summary,
        "results": results,
    }


if __name__ == "__main__":
    batch = run_synthetic_lr_batch(n_per_config=1, persist=True)
    print("=== Summary ===")
    for k, v in batch["summary"].items():
        print(f"{k}: {v}")