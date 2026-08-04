# API Service

This package exposes the FastAPI service surface for creating canonical records through HTTP. It reuses the same validation, routing, and persistence logic used by the synthetic pipeline so the API stays aligned with the batch path.

## What this package does

The API layer provides a small authenticated service for record creation and health checks. Its primary responsibility is to accept a canonical record request, validate it, route it, and persist it to the correct destination.

## Main flow

The live request path is:

`FastAPI request -> /records -> map/validate -> choose_destination -> save_record`

That keeps the API consistent with the rest of the repo:

- canonical record semantics come from `src.persist`
- validation comes from `src.validate`
- storage comes from `src.persist.filesystem_store`

## Files

### `main.py`
Application setup, token protection, and general FastAPI wiring.

Main responsibilities:
- create the FastAPI app,
- enforce authentication,
- expose health/root endpoints,
- mount routers.

Key functions:
- `require_api_token`
- `root`
- `health`
- `main`

### `routes.py`
Record creation route implementation.

Main dependencies:
- `src.normalize.canonical_mapper`
- `src.persist.filesystem_store`
- `src.validate.confidence_checks`
- `src.validate.review_routing`

Key functions:
- `records_health`
- `create_record`

## Dependency flow

The API is intentionally thin:

- request input enters through FastAPI,
- records are mapped or validated into canonical form,
- destination is chosen via review-routing logic,
- the record is saved to normalized storage or review queue.

This means the API is not a separate business logic layer; it is a service wrapper around the canonical pipeline.

## What to inspect first

If you are debugging the API, inspect these files in order:

1. `main.py`
2. `routes.py`
3. `src.validate.confidence_checks`
4. `src.validate.review_routing`
5. `src.persist.filesystem_store`

## Commands

Run the API locally:

```bash
python -m uvicorn src.api.main:app --reload
```

Run the full test slice for the API route:

```bash
pytest -q tests/test_api_records.py
```

If you need to inspect the mounted routes manually, open the FastAPI docs after starting the server.

## Notes

- The API uses the same canonical persistence path as the batch runner.
- If routing or validation changes, the API README should be updated together with the normalize and validate docs.
- Keep this package documented at the service level; avoid duplicating the deeper storage or validation details here.
