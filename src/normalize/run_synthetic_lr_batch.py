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
    num_candidates: int = 1,
    flaw_types: list[str] | None = None,
    difficulties: list[str] | None = None,
    include_debug: bool = False,
    diversity_version: str = "v1",
    diversity_modes: list[str] | None = None,
    corresponding_lane_edit_reminder: bool = True,

) -> dict:

    """Run a small sweep across flaw types, difficulties, and diversity modes.

    Uses the LLM_BACKEND env var (default: openai) via get_llm_client().


    MLflow instrumentation:
    - One parent run per batch (params: backend, model, n_per_config, configs, git_sha)
    - One nested run per (flaw_type, difficulty, diversity_mode) config (per-lane metrics)
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

    flaw_types = flaw_types or ["causal", "necessary_vs_sufficient", "sampling"]
    difficulties = difficulties or ["easy", "medium"]
    diversity_modes = diversity_modes or ["baseline"]
    configs = [(f, d, dm) for f in flaw_types for d in difficulties for dm in diversity_modes]



    tracker_tags = {
        "backend": backend_name,
        "git_sha": get_git_sha(),
        "pipeline": "synthetic_lr",
    }
    run_name = (
        f"batch_{backend_name}_{n_per_config}per_"
        f"{num_candidates}cand_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )

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
                "num_candidates": num_candidates,
                "num_configs": len(configs),
                "config_names": ",".join(f"{f}:{d}:{dm}" for f, d, dm in configs),
                "flaw_types": ",".join(flaw_types),
                "difficulties": ",".join(difficulties),
                "persist": persist,
                "include_debug": include_debug,
                "diversity_version": diversity_version,
                "diversity_modes": ",".join(diversity_modes),
                "corresponding_lane_edit_reminder": corresponding_lane_edit_reminder,
           }
        )


        destination_counts: Counter = Counter()
        status_counts: Counter = Counter()
        quality_status_counts: Counter = Counter()
        quality_flag_counts: Counter = Counter()
        runtime_error_counts: Counter = Counter()
        backend_counts: Counter = Counter()

        diversity_mode_counts: Counter = Counter()
        diversity_mode_status_counts: Counter = Counter()

        results = []
        all_generation_meta = []  # for batch-level aggregation

        for flaw_type, difficulty, diversity_mode in configs:
            lane_status: Counter = Counter()
            lane_quality: Counter = Counter()
            lane_errors = 0
            lane_meta = []  # per-lane generation metadata

            with tracker.nested_run(
                run_name=f"{flaw_type}_{difficulty}_{diversity_mode}",
                tags={
                    "flaw_type": flaw_type, 
                    "difficulty": difficulty, 
                    "diversity_mode": diversity_mode, 
                    "diversity_version": diversity_version,
                },
            ):
                tracker.log_params(
                    {
                        "flaw_type": flaw_type,
                        "difficulty": difficulty,
                        "diversity_mode": diversity_mode,
                        "diversity_version": diversity_version,
                        "num_candidates": num_candidates,
                        "include_debug": include_debug,
                        "persist": persist,
                    }
                )
                for _ in range(n_per_config):
                    try:
                        if corresponding_lane_edit_reminder and not diversity_version:
                            raise ValueError("diversity_version must be set when lane edit reminder is enabled.")

                        # Batch-level tracking may record diversity controls before they are wired into
                        # the lane. Only pass kwargs here that run_synthetic_lr_lane() explicitly accepts.

                        out = run_synthetic_lr_lane(
                            flaw_type=flaw_type,
                            difficulty=difficulty,
                            client=client,
                            model=model,
                            persist=persist,
                            num_candidates=num_candidates,
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
                    diversity_mode_counts[diversity_mode] += 1
                    diversity_mode_status_counts[(diversity_mode, out["status"])] += 1
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
                    gen_meta = out.get("generation_meta")
                    if gen_meta is not None:
                        # Tag parent run once with the actual model served
                        if not all_generation_meta:
                            tracker.set_tag("model_actual", gen_meta.model)
                        lane_meta.append(gen_meta)
                        all_generation_meta.append(gen_meta)

                    item_result = {
                        "flaw_type": flaw_type,
                        "difficulty": difficulty,
                        "diversity_mode": diversity_mode,
                        "diversity_version": diversity_version,
                        "status": out["status"],
                        "destination": dest,
                        "quality_status": q_status,
                        "quality_flags": list(cq.get("flags") or []),
                        "saved_path": out.get("saved_path"),
                        "error": out.get("error"),
                        "selected_candidate_index": out.get("selected_candidate_index"),
                        "selection_reason": out.get("selection_reason"),

                    }
                    if include_debug:
                        item_result["candidate_scores"] = out.get("candidate_scores")
                    results.append(item_result)


                # Per-lane metrics
                total_lane = n_per_config
                lane_gen_metrics = _aggregate_generation_metrics(lane_meta)
                tracker.log_metrics(
                    {
                        "lane_items": total_lane,
                        "lane_valid": lane_status.get("valid", 0),
                        "lane_needs_review": lane_status.get("needs_review", 0),
                        "lane_runtime_errors": lane_errors,
                        "lane_quality_ok": lane_quality.get("pass", 0),
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
            "batch_id": run_name,
            "status_counts": dict(status_counts),
            "destination_counts": {str(k): v for k, v in destination_counts.items()},
            "quality_status_counts": dict(quality_status_counts),
            "quality_flag_counts": dict(quality_flag_counts),
            "runtime_error_counts": dict(runtime_error_counts),
            "backend_counts": dict(backend_counts),
            "diversity_mode_counts": dict(diversity_mode_counts),
            "diversity_mode_status_counts": {
                f"{mode}:{status}": count
                for (mode, status), count in diversity_mode_status_counts.items()
            },
            "generation_metrics": batch_gen_metrics,
            "total_items": len(results),
            "num_candidates": num_candidates,
            "n_per_config": n_per_config,
            "flaw_types": flaw_types,
            "difficulties": difficulties,
            "num_configs": len(configs),
            "diversity_version": diversity_version,
            "diversity_modes": diversity_modes,
            "corresponding_lane_edit_reminder": corresponding_lane_edit_reminder,
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
            tracker.set_tag("batch_id", run_name)
            tracker.set_tag("batch_summary_path", str(summary_path))
        record_paths = [r["saved_path"] for r in results if r.get("saved_path")]

        return {
            "summary": summary,
            "results": results,
            "summary_path": str(summary_path) if summary_path else None,
            "artifacts": {
                "batch_summary_path": str(summary_path) if summary_path else None,
                "record_paths": record_paths,
            },
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

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Run synthetic LR generation batch.")
    
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Override the model name passed to the active backend.",
    )
    parser.add_argument(
        "--experiment",
        type=str,
        default="synthetic_lr",
        help="MLflow experiment name.",
    )

    parser.add_argument(
        "--summary-dir",
        type=str,
        default="data/normalized/batches",
        help="Directory for persisted batch summaries.",
    )

    parser.add_argument(
        "--flaw-types",
        nargs="+",
        choices=["causal", "necessary_vs_sufficient", "sampling"],
        default=None,
        help="One or more flaw types to run.",
    )

    parser.add_argument(
        "--difficulties",
        nargs="+",
        choices=["easy", "medium", "hard"],
        default=None,
        help="One or more difficulty levels to run.",
    )

    parser.add_argument(
        "--include-debug",
        dest="include_debug",
        action="store_true",
        help="Include debug-only fields in batch results.",
    )
    parser.add_argument(
        "--no-include-debug",
        dest="include_debug",
        action="store_false",
        help="Exclude debug-only fields in batch results.",
    )
    parser.set_defaults(include_debug=False)

    parser.add_argument(
        "--n-per-config",
        type=int,
        default=1,
        help="Number of items to generate per (flaw_type, difficulty) config. Default: 1.",
    )
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="Do not write batch summary artifacts to disk.",
    )
    parser.add_argument(
        "--no-track",
        action="store_true",
        help="Disable MLflow tracking for this run.",
    )
    parser.add_argument(
        "--num-candidates",
        type=int,
        default=1,
        help="Number of candidates to generate per item before selection. Default: 1.",
    )
    parser.add_argument(
        "--diversity-version",
        type=str,
        choices=["v1"],
        default="v1",
        help="Diversity prompt/control version label.",
    )

    parser.add_argument(
        "--diversity-modes",
        nargs="+",
        choices=["baseline", "paraphrase", "structure", "reasoning_angle"],
        default=None,
        help="One or more diversity modes to apply, e.g. baseline paraphrase structure.",
    )

    parser.add_argument(
        "--corresponding-lane-edit-reminder",
        dest="corresponding_lane_edit_reminder",
        action="store_true",
        help="Enable reminder that lane-level prompt/schema edits must stay aligned.",
    )
    parser.add_argument(
        "--no-corresponding-lane-edit-reminder",
        dest="corresponding_lane_edit_reminder",
        action="store_false",
        help="Disable lane edit reminder.",
    )
    parser.set_defaults(corresponding_lane_edit_reminder=True)

    
    args = parser.parse_args()

    batch = run_synthetic_lr_batch(
        n_per_config=args.n_per_config,
        persist=not args.no_persist,
        model=args.model,
        track=not args.no_track,
        experiment=args.experiment,
        summary_dir=args.summary_dir,
        num_candidates=args.num_candidates,
        flaw_types=args.flaw_types,
        difficulties=args.difficulties,
        include_debug=args.include_debug,
        diversity_version=args.diversity_version,
        diversity_modes=args.diversity_modes,
        corresponding_lane_edit_reminder=args.corresponding_lane_edit_reminder,
    )


    print("=== Summary ===")
    for k, v in batch["summary"].items():
        print(f"{k}: {v}")
    if batch.get("summary_path"):
        print(f"\nSummary written to: {batch['summary_path']}")

if __name__ == "__main__":
    main()
