# Validation and Routing

This package decides whether a canonical record is acceptable for normalized storage or should be sent to review. It contains the lightweight validation and destination-routing logic used by both the API and the synthetic LR pipeline.

## What this package does

The validation layer answers two questions:

- Is the canonical record structurally valid and confident enough to keep?
- If not, where should it go in the review queue and why?

That makes this package the final decision point before persistence.

## Main flow

The live decision flow is:

`CanonicalRecord -> validate_record -> choose_destination -> save_record`

It is used by both:

- `src.normalize.run_synthetic_lr_lane`
- `src.api.routes`

## Files

### `confidence_checks.py`
Final validation pass over the canonical record.

Main responsibilities:
- enforce record-level constraints,
- normalize or finalize canonical record content when needed,
- keep the record in the expected canonical shape.

Key function:
- `validate_record`

### `review_routing.py`
Decision logic for where a record should go when it is not accepted into normalized storage.

Main responsibilities:
- choose a destination,
- attach a review reason when needed,
- keep review routing consistent across API and batch flows.

Key function:
- `choose_destination`

## Dependency flow

This package depends on the canonical record models from `src.persist` and is called by the normalize and API layers.

Upstream callers:
- `src.normalize.run_synthetic_lr_lane`
- `src.api.routes`

Downstream consumer:
- `src.persist.filesystem_store.save_record`

## What to inspect first

If you are debugging routing decisions, inspect these files in order:

1. `confidence_checks.py`
2. `review_routing.py`
3. `src.persist.filesystem_store`
4. caller code in `src.normalize.run_synthetic_lr_lane` or `src.api.routes`

## Commands

Run the relevant tests:

```bash
pytest -q tests/test_synthetic_lr_review_routing.py tests/test_api_records.py
```

Inspect the live functions:

```bash
grep -R "def validate_record\|def choose_destination" -n src/validate src/normalize src/api
```

## Notes

- This package is intentionally small, but it is important because it controls the boundary between accepted records and review artifacts.
- If routing semantics change, update this README together with the API and normalize docs.
- Keep this package focused on decision logic; avoid moving persistence code here.
