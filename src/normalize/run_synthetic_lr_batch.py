from __future__ import annotations

import json
import os
import statistics
from collections import Counter
from datetime import datetime
from pathlib import Path

from src.llm_client import get_llm_client
from src.normalize.run_synthetic_lr_lane import run_synthetic_lr_lane
from src.tracking import MLflowTracker, get_git_sha


# gpt-4o-mini pricing as of July 2026 (per 1M tokens). Update as needed.
# Kept in-module so cost estimation is transparent and version-controlled.
MODEL_PRICING_USD_PER_MTOK = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o-mini-2024-07-18": {"input": 0.15, "output": 0.60},
    # Local models: no per-token cost
    "qwen3:8b": {"input": 0.0, "output": 0.0},
}


def _estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate USD cost for a single generation call. Returns 0.0 if model is unknown."""
    pricing = MODEL_PRICING_USD_PER_MTOK.get(model)
    if not pricing:
        return 0.0
    return (
        prompt_tokens * pricing["input"] / 1_000_000
        + completion_tokens * pricing["output"] / 1_000_000
    )


def _aggregate_generation_metrics(meta_list: list) -> dict:
    """Compute aggregate metrics across a list of GenerationMeta objects.

    Handles missing/None fields gracefully — some backends may not report tokens.
    Returns 0.0 for empty input.
    """
    if not meta_list:
        return {
            "prompt_tokens_total": 0,
            "completion_tokens_total": 0,
            "tokens_total": 0,
            "estimated_cost_usd": 0.0,
            "latency_ms_avg": 0.0,
            "latency_ms_p50": 0.0,
            "latency_ms_p95": 0.0,
            "items_with_meta": 0,
        }

    prompt_tokens = [m.prompt_tokens or 0 for m in meta_list]
    completion_tokens = [m.completion_tokens or 0 for m in meta_list]
    latencies_ms = [m.latency_seconds * 1000 for m in meta_list if m.latency_seconds is not None]

    cost = sum(
        _estimate_cost_usd(m.model, m.prompt_tokens or 0, m.completion_tokens or 0)
        for m in meta_list
    )

    def _p(values: list, pct: float) -> float:
        if not values:
            return 0.0
        return float(statistics.quantiles(values, n=100)[int(pct) - 1]) if len(values) >= 2 else float(values[0])

    return {
        "prompt_tokens_total": sum(prompt_tokens),
        "completion_tokens_total": sum(completion_tokens),
        "tokens_total": sum(prompt_tokens) + sum(completion_tokens),
        "estimated_cost_usd": round(cost, 6),
        "latency_ms_avg": round(statistics.mean(latencies_ms), 2) if latencies_ms else 0.0,
        "latency_ms_p50": round(_p(latencies_ms, 50), 2),
        "latency_ms_p95": round(_p(latencies_ms, 95), 2),
        "items_with_meta": len(meta_list),
    }


def run_synthetic_lr_batch(
    n_per_config: int = 2,
    persist: bool = True,
    model: str | None = None,
    track: bool = True,
    experiment: str = "synthetic_lr",
    summary_dir: str | Path = "data/normalized/batches",
) -> dict:
    """Run a small sweep across flaw types and difficulties.

    Uses the LLM_BACKEND env var (default: ollama) via get_llm_client().

    MLflow instrumentation:
    - One parent run per batch (params: backend, model, n_per_config, configs, git_sha)
    - One nested run per (flaw_type, difficulty) config (per-lane metrics)
    - Batch-level metrics + summary artifact logged on the parent run
    - Token/cost/latency aggregates from GenerationMeta on both parent and nested runs
    - Disable via track=False or TRACKING_DISABLED=1 (useful for tests)
    """
    client = get_llm_client()
    backend_name = getattr(client, "backend_name", "unknown")
    model_name = (
        model
        or getattr(client, "model", None)
        or os.getenv("OPENAI_MODEL")
        or os.getenv("OLLAMA_MODEL")
        or "unknown"
    )

    configs = [
        ("causal", "easy"),
        ("causal", "medium"),
        ("necessary_vs_sufficient", "easy"),
        ("necessary_vs_sufficient", "medium"),
    ]

    tracker_tags = {
        "backend": backend_name,
        "git_sha": get_git_sha(),
        "pipeline": "synthetic_lr",
    }
    run_name = f"batch_{backend_name}_{n_per_config}per_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    with MLflowTracker(
        experiment=experiment,
        run_name=run_name,
        tags=tracker_tags,
        disabled=not track,
    ) as tracker:
        tracker.log_params(
            {
                "backend": backend_name,
                "model": model_name,
                "n_per_config": n_per_config,
                "num_configs": len(configs),
                "config_names": ",".join(f"{f}:{d}" for f, d in configs),
                "persist": persist,
            }
        )

        destination_counts: Counter = Counter()
        status_counts: Counter = Counter()
        quality_status_counts: Counter = Counter()
        quality_flag_counts: Counter = Counter()
        runtime_error_counts: Counter = Counter()
        backend_counts: Counter = Counter()

        results = []
        all_generation_meta = []  # for batch-level aggregation

        for flaw_type, difficulty in configs:
            lane_status: Counter = Counter()
            lane_quality: Counter = Counter()
            lane_errors = 0
            lane_meta = []  # per-lane generation metadata

            with tracker.nested_run(
                run_name=f"{flaw_type}_{difficulty}",
                tags={"flaw_type": flaw_type, "difficulty": difficulty},
            ):
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
                        lane_errors += 1

                        out = {
                            "status": "needs_review",
                            "destination": ("review", "generation_runtime_error"),
                            "content_quality": None,
                            "saved_path": None,
                            "error": str(exc),
                            "generation_meta": None,
                        }

                    status_counts[out["status"]] += 1
                    lane_status[out["status"]] += 1
                    dest = out["destination"]
                    destination_counts[dest] += 1
                    backend_counts[backend_name] += 1

                    cq = out.get("content_quality") or {}
                    q_status = cq.get("status")
                    if q_status:
                        quality_status_counts[q_status] += 1
                        lane_quality[q_status] += 1
                    for flag in cq.get("flags") or []:
                        quality_flag_counts[flag] += 1

                    # Collect generation metadata if present
                                        # Collect generation metadata if present
                    gen_meta = out.get("generation_meta")
                    if gen_meta is not None:
                        # Tag parent run once with the actual model served
                        if not all_generation_meta:
                            tracker.set_tag("model_actual", gen_meta.model)
                        lane_meta.append(gen_meta)
                        all_generation_meta.append(gen_meta)

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

                # Per-lane metrics
                total_lane = n_per_config
                lane_gen_metrics = _aggregate_generation_metrics(lane_meta)
                tracker.log_metrics(
                    {
                        "lane_items": total_lane,
                        "lane_valid": lane_status.get("valid", 0),
                        "lane_needs_review": lane_status.get("needs_review", 0),
                        "lane_runtime_errors": lane_errors,
                        "lane_quality_ok": lane_quality.get("ok", 0),
                        "lane_acceptance_rate": (
                            lane_status.get("valid", 0) / total_lane
                            if total_lane
                            else 0.0
                        ),
                        **{f"lane_{k}": v for k, v in lane_gen_metrics.items()},
                    }
                )

        # Batch-level generation aggregates
        batch_gen_metrics = _aggregate_generation_metrics(all_generation_meta)

        summary = {
            "status_counts": dict(status_counts),
            "destination_counts": {str(k): v for k, v in destination_counts.items()},
            "quality_status_counts": dict(quality_status_counts),
            "quality_flag_counts": dict(quality_flag_counts),
            "runtime_error_counts": dict(runtime_error_counts),
            "backend_counts": dict(backend_counts),
            "generation_metrics": batch_gen_metrics,
            "total_items": len(results),
        }

        # Batch-level rollup metrics
        total = len(results) or 1
        tracker.log_metrics(
            {
                "total_items": len(results),
                "total_valid": status_counts.get("valid", 0),
                "total_needs_review": status_counts.get("needs_review", 0),
                "total_runtime_errors": sum(runtime_error_counts.values()),
                "acceptance_rate": status_counts.get("valid", 0) / total,
                **batch_gen_metrics,
            }
        )

        # Persist summary as artifact
        summary_path = None
        if persist:
            summary_path = _write_summary(summary, results, summary_dir, run_name)
            tracker.log_artifact(summary_path)

        return {
            "summary": summary,
            "results": results,
            "summary_path": str(summary_path) if summary_path else None,
        }


def _write_summary(
    summary: dict,
    results: list,
    summary_dir: str | Path,
    run_name: str,
) -> Path:
    """Write batch summary + results to a timestamped JSON file."""
    out_dir = Path(summary_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{run_name}.json"
    payload = {"summary": summary, "results": results}
    out_path.write_text(json.dumps(payload, indent=2, default=str))
    return out_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run synthetic LR generation batch.")
    parser.add_argument(
        "--n-per-config",
        type=int,
        default=1,
        help="Number of items to generate per (flaw_type, difficulty) config. Default: 1 (dry-run).",
    )
    args = parser.parse_args()

    batch = run_synthetic_lr_batch(n_per_config=args.n_per_config, persist=True)
    print("=== Summary ===")
    for k, v in batch["summary"].items():
        print(f"{k}: {v}")
    if batch.get("summary_path"):
        print(f"\nSummary written to: {batch['summary_path']}")