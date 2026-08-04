# Project Status

## Current state

The repository is in a lean, stable **OpenAI-primary synthetic LR** stage. The active pipeline now runs cleanly across generation, validation, canonical mapping, review routing, persistence, batch orchestration, and evaluation.

## Verified status

- Full test suite: 74 passed, 1 skipped.
- Active synthetic LR path is wired end to end.
- Canonical metadata now resolves from `metadata` first, with legacy fallbacks preserved where needed.
- The retired `LSATInfo` path is no longer part of the active runtime surface.
- Multi-candidate lane selection, batch summaries, MLflow tracking, and filesystem persistence are working.
- Evaluation now carries `flaw_type`, `difficulty`, load stats, and per-flaw-family aggregates through the judge pipeline.

## Active focus

Near-term work is about tightening quality, not fixing core wiring:

- improve phrasing diversity across flaw families,
- reduce stock or template-like item feel,
- strengthen distractor distinction,
- keep synthetic quality and human review rubrics lightweight and aligned,
- avoid reintroducing duplicate or legacy test surfaces.

## Current judgment

The codebase is ready as a stable synthetic-LR baseline. It is not fully freeze-ready for a v1 item bank until another small audit batch confirms stronger item diversity and cleaner flaw-family separation.

## Next actions

- Run another small persisted batch focused on phrasing diversity.
- Tighten prompt and quality checks to reduce memorizable patterns.
- Keep tests mapped to live production seams only.
- Update docs in step with any schema or routing changes.
- Freeze `baseline_v1` and `eval_set_v1` only after quality improves, not just validity.