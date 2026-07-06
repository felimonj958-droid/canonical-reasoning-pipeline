"""Render a Markdown evaluation report from a batch summary + evaluation JSON."""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

# gpt-4o-mini pricing baked in (keep in sync with run_synthetic_lr_batch.py)
GENERATOR_PRICING = {
    "input": 0.15,
    "output": 0.60,
}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _load_record_by_id(records_dir: Path, record_id: str) -> dict | None:
    p = records_dir / f"{record_id}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())


def _render_item(record: dict, judge_result: dict) -> str:
    content = record.get("content") or {}
    # Note: pipeline currently stores the stimulus text in `question_stem`.
    # The actual LSAT question stem and correct_answer are not yet captured — Session 1.5 fix.
    stimulus = (content.get("stimulus") or content.get("question_stem") or "").strip()
    question = (content.get("question") or "").strip() or "_(question stem not captured — see Session 1.5)_"
    choices = content.get("answer_choices") or []
    correct = (content.get("correct_answer") or "").strip() or "_(not captured — see Session 1.5)_"
    gen = record.get("generation") or {}

    choices_md = "\n".join(
        f"- **({c.get('label', '?')})** {c.get('text', '')}"
        for c in choices
    ) if choices else "_(no answer choices)_"

    score = judge_result.get("score") or {}
    total = judge_result.get("score_total") or 0
    notes = judge_result.get("notes") or ""

    return f"""**Record ID:** `{record.get('record_id', 'unknown')}`
**Flaw type:** {gen.get('flaw_type', '?')} | **Difficulty:** {gen.get('difficulty', '?')}
**Total score:** {total}/25 — argument_coherence={score.get('argument_coherence', '?')}, flaw_fidelity={score.get('flaw_fidelity', '?')}, question_stem={score.get('question_stem_quality', '?')}, distractors={score.get('distractor_plausibility', '?')}, correct_answer={score.get('correct_answer_precision', '?')}

**Stimulus:**
> {stimulus}

**Question:** {question}

{choices_md}

**Correct:** {correct}

**Judge notes:** {notes}
"""


def render_report(
    eval_path: Path,
    batch_summary_path: Path | None = None,
    records_dir: Path = Path("data/normalized/records"),
    output_dir: Path = Path("data/reports"),
) -> Path:
    eval_data = _load_json(eval_path)
    batch_summary = _load_json(batch_summary_path) if batch_summary_path else None

    aggregates = eval_data["aggregates"]
    dim_means = aggregates.get("dimension_means", {})
    results = eval_data.get("results", [])

    # Per-config breakdown — need to look up records
    scored_results = [r for r in results if r.get("status") == "scored"]

    per_config = {}
    for r in scored_results:
        rec = _load_record_by_id(records_dir, r["record_id"])
        if rec is None:
            continue
        gen = rec.get("generation") or {}
        key = f"{gen.get('flaw_type', '?')}_{gen.get('difficulty', '?')}"
        per_config.setdefault(key, []).append(r["score_total"])

    per_config_rows = []
    for k, totals in sorted(per_config.items()):
        avg = sum(totals) / len(totals) if totals else 0
        hq = sum(1 for t in totals if t >= 20)
        hq_rate = hq / len(totals) if totals else 0
        per_config_rows.append(
            f"| {k} | {len(totals)} | {avg:.1f} | {hq}/{len(totals)} ({hq_rate:.0%}) |"
        )

    # Best + worst samples
    best_result = max(scored_results, key=lambda r: r["score_total"], default=None)
    worst_result = min(scored_results, key=lambda r: r["score_total"], default=None)

    best_section = ""
    if best_result:
        rec = _load_record_by_id(records_dir, best_result["record_id"])
        if rec:
            best_section = f"## Sample high-scoring item\n\n{_render_item(rec, best_result)}\n"

    worst_section = ""
    if worst_result and worst_result["record_id"] != (best_result or {}).get("record_id"):
        rec = _load_record_by_id(records_dir, worst_result["record_id"])
        if rec:
            worst_section = f"## Sample low-scoring item + judge notes\n\n{_render_item(rec, worst_result)}\n"

    # Generation cost from batch summary if available
    generator_cost = "n/a"
    generator_count = "n/a"
    if batch_summary:
        gen_metrics = batch_summary.get("summary", {}).get("generation_metrics", {})
        generator_cost = f"${gen_metrics.get('estimated_cost_usd', 0):.6f}"
        generator_count = batch_summary.get("summary", {}).get("total_items", "n/a")

    md = f"""# Batch Evaluation Report

**Batch:** `{eval_data.get('source_batch', 'unknown')}`
**Evaluation run:** `{eval_data.get('run_name', 'unknown')}`
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary

- **Items evaluated:** {aggregates['items_evaluated']}
- **Items scored:** {aggregates['items_scored']}
- **Parse errors:** {aggregates['items_parse_error']}
- **Runtime errors:** {aggregates['items_runtime_error']}
- **Judge model:** {eval_data.get('judge_model', 'unknown')}
- **Judge cost:** ${eval_data.get('judge_cost_usd', 0):.6f}
- **Generator batch size:** {generator_count} items at {generator_cost}
- **Mean quality score:** {aggregates.get('score_total_mean', 0):.2f} / 25
- **High-quality items (>=20):** {aggregates['high_quality_count']}/{aggregates['items_scored']} ({aggregates['high_quality_rate']:.0%})

## Score distribution

| Dimension | Mean |
| --- | --- |
| Argument coherence | {dim_means.get('argument_coherence', 0):.2f} |
| Flaw fidelity | {dim_means.get('flaw_fidelity', 0):.2f} |
| Question stem quality | {dim_means.get('question_stem_quality', 0):.2f} |
| Distractor plausibility | {dim_means.get('distractor_plausibility', 0):.2f} |
| Correct answer precision | {dim_means.get('correct_answer_precision', 0):.2f} |

## Per-config breakdown

| Config | Items | Avg score | High-quality rate |
| --- | --- | --- | --- |
{chr(10).join(per_config_rows) if per_config_rows else '| _no per-config data available_ | | | |'}

{best_section}
{worst_section}
"""

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{eval_data['run_name']}.md"
    output_path.write_text(md)
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.render_batch_report <eval_json_path> [<batch_summary_path>]")
        sys.exit(1)

    eval_path = Path(sys.argv[1])
    batch_summary_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    report_path = render_report(eval_path, batch_summary_path)
    print(f"Report written to: {report_path}")