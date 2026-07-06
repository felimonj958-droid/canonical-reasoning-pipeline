"""Batch evaluation: score every record in a batch, aggregate, log to MLflow."""
from __future__ import annotations

import json
import os
import statistics
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.evaluate.judge_rubric import (
    HIGH_QUALITY_THRESHOLD,
    RUBRIC_DIMENSIONS,
    JudgeScore,
)
from src.evaluate.llm_judge import judge_record, JudgeResult
from src.llm_client import get_llm_client
from src.tracking import MLflowTracker, get_git_sha


# Judge cost estimation — same table as batch script would ideally share.
# Kept separate for now; consolidate later if it drifts.
JUDGE_MODEL_PRICING_USD_PER_MTOK = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o-mini-2024-07-18": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
}


def _estimate_judge_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = JUDGE_MODEL_PRICING_USD_PER_MTOK.get(model)
    if not pricing:
        return 0.0
    return (
        prompt_tokens * pricing["input"] / 1_000_000
        + completion_tokens * pricing["output"] / 1_000_000
    )


def _load_records_from_batch_summary(batch_summary_path: Path) -> list[dict]:
    """Load canonical records referenced by a batch summary JSON."""
    payload = json.loads(batch_summary_path.read_text())
    results = payload.get("results", [])

    records = []
    for r in results:
        saved_path = r.get("saved_path")
        if not saved_path:
            continue
        p = Path(saved_path)
        if not p.exists():
            continue
        try:
            records.append(json.loads(p.read_text()))
        except Exception:
            continue
    return records


def aggregate_scores(judge_results: list[JudgeResult]) -> dict:
    """Compute batch-level aggregate metrics from judge results."""
    scored = [r for r in judge_results if r.status == "scored" and r.score is not None]
    parse_errors = [r for r in judge_results if r.status == "parse_error"]
    runtime_errors = [r for r in judge_results if r.status == "runtime_error"]

    if not scored:
        return {
            "items_evaluated": len(judge_results),
            "items_scored": 0,
            "items_parse_error": len(parse_errors),
            "items_runtime_error": len(runtime_errors),
            "score_total_mean": 0.0,
            "high_quality_count": 0,
            "high_quality_rate": 0.0,
            "dimension_means": {dim: 0.0 for dim in RUBRIC_DIMENSIONS},
        }

    totals = [r.score.total for r in scored]
    dim_means = {}
    for dim in RUBRIC_DIMENSIONS:
        values = [getattr(r.score, dim) for r in scored]
        dim_means[dim] = round(statistics.mean(values), 2)

    return {
        "items_evaluated": len(judge_results),
        "items_scored": len(scored),
        "items_parse_error": len(parse_errors),
        "items_runtime_error": len(runtime_errors),
        "score_total_mean": round(statistics.mean(totals), 2),
        "score_total_median": statistics.median(totals),
        "score_total_min": min(totals),
        "score_total_max": max(totals),
        "high_quality_count": sum(1 for t in totals if t >= HIGH_QUALITY_THRESHOLD),
        "high_quality_rate": round(
            sum(1 for t in totals if t >= HIGH_QUALITY_THRESHOLD) / len(totals), 3
        ),
        "dimension_means": dim_means,
    }


def evaluate_batch(
    batch_summary_path: str | Path,
    output_dir: str | Path = "data/evaluations",
    track: bool = True,
    experiment: str = "synthetic_lr_evaluation",
    limit: Optional[int] = None,
) -> dict:
    """Evaluate every record in a batch. Log per-item + aggregate to MLflow.

    Args:
        batch_summary_path: Path to a batch summary JSON (from run_synthetic_lr_batch).
        output_dir: Where to write the evaluation JSON.
        track: Whether to log to MLflow.
        experiment: MLflow experiment name.
        limit: Optional cap on records evaluated (for smoke tests).

    Returns:
        Dict with aggregate metrics + per-record judge results.
    """
    batch_summary_path = Path(batch_summary_path)
    if not batch_summary_path.exists():
        raise FileNotFoundError(f"Batch summary not found: {batch_summary_path}")

    records = _load_records_from_batch_summary(batch_summary_path)
    if limit:
        records = records[:limit]

    if not records:
        raise ValueError(f"No records found via batch summary at {batch_summary_path}")

    client = get_llm_client()
    judge_model = os.getenv("JUDGE_MODEL", "gpt-4o-mini")
    judge_model_expected = judge_model
    batch_name = batch_summary_path.stem
    run_name = f"eval_{batch_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    tracker_tags = {
        "backend": getattr(client, "backend_name", "unknown"),
        "git_sha": get_git_sha(),
        "pipeline": "synthetic_lr_evaluation",
        "source_batch": batch_name,
    }

    with MLflowTracker(
        experiment=experiment,
        run_name=run_name,
        tags=tracker_tags,
        disabled=not track,
    ) as tracker:
        tracker.log_params(
            {
                "source_batch": batch_name,
                "num_records": len(records),
                "judge_model_expected": judge_model_expected,
                "high_quality_threshold": HIGH_QUALITY_THRESHOLD,
            }
        )

        judge_results = []
        for record in records:
            result = judge_record(record, client=client, judge_model=judge_model)
            judge_results.append(result)

        # Tag actual judge model from first successful score
        for r in judge_results:
            if r.judge_model:
                tracker.set_tag("judge_model_actual", r.judge_model)
                break

        aggregates = aggregate_scores(judge_results)

        # Cost + latency aggregates
        prompt_tokens_total = sum(r.prompt_tokens for r in judge_results)
        completion_tokens_total = sum(r.completion_tokens for r in judge_results)
        judge_model_for_cost = next((r.judge_model for r in judge_results if r.judge_model), "unknown")
        judge_cost = _estimate_judge_cost(
            judge_model_for_cost, prompt_tokens_total, completion_tokens_total
        )
        latencies_ms = [r.latency_seconds * 1000 for r in judge_results if r.latency_seconds]

        tracker.log_metrics(
            {
                "items_evaluated": aggregates["items_evaluated"],
                "items_scored": aggregates["items_scored"],
                "items_parse_error": aggregates["items_parse_error"],
                "items_runtime_error": aggregates["items_runtime_error"],
                "score_total_mean": aggregates["score_total_mean"],
                "high_quality_count": aggregates["high_quality_count"],
                "high_quality_rate": aggregates["high_quality_rate"],
                "judge_prompt_tokens_total": prompt_tokens_total,
                "judge_completion_tokens_total": completion_tokens_total,
                "judge_tokens_total": prompt_tokens_total + completion_tokens_total,
                "judge_estimated_cost_usd": round(judge_cost, 6),
                "judge_latency_ms_avg": (
                    round(statistics.mean(latencies_ms), 2) if latencies_ms else 0.0
                ),
                **{f"dim_{k}_mean": v for k, v in aggregates["dimension_means"].items()},
            }
        )

        # Persist evaluation output
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        eval_path = output_dir / f"{run_name}.json"

        eval_payload = {
            "run_name": run_name,
            "source_batch": batch_name,
            "judge_model": judge_model_for_cost,
            "aggregates": aggregates,
            "judge_cost_usd": round(judge_cost, 6),
            "judge_tokens_total": prompt_tokens_total + completion_tokens_total,
            "results": [
                {
                    "record_id": r.record_id,
                    "status": r.status,
                    "score": r.score.model_dump() if r.score else None,
                    "score_total": r.score.total if r.score else None,
                    "notes": r.score.notes if r.score else "",
                    "error": r.error,
                    "prompt_tokens": r.prompt_tokens,
                    "completion_tokens": r.completion_tokens,
                    "latency_seconds": r.latency_seconds,
                }
                for r in judge_results
            ],
        }

        eval_path.write_text(json.dumps(eval_payload, indent=2, default=str))
        tracker.log_artifact(eval_path)

        return {
            "run_name": run_name,
            "eval_path": str(eval_path),
            "aggregates": aggregates,
            "judge_cost_usd": round(judge_cost, 6),
        }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m src.evaluate.run_evaluation <batch_summary_path> [limit]")
        sys.exit(1)

    batch_path = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else None

    result = evaluate_batch(batch_path, limit=limit)
    print(f"\n=== Evaluation complete: {result['run_name']} ===")
    print(f"Cost: ${result['judge_cost_usd']}")
    print(f"Saved: {result['eval_path']}")
    print("\nAggregates:")
    for k, v in result["aggregates"].items():
        print(f"  {k}: {v}")