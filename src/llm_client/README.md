# LLM Client Abstraction

This package provides the model-calling abstraction used throughout the repository. It keeps generation and evaluation code independent from a specific backend while still supporting the current OpenAI-primary runtime path.

## What this package does

The client layer is responsible for:

- defining a shared request/response interface,
- selecting the active backend,
- sending generation requests,
- returning normalized responses with token and model metadata.

That lets the rest of the codebase call `get_llm_client()` rather than hard-coding a provider.

## Files

### `base.py`
Backend-agnostic request/response abstractions.

Main responsibilities:
- define the `GenerationRequest` contract,
- define response types,
- expose the common client interface.

Use this file when you need to know what any backend must implement.

### `openai_client.py`
OpenAI implementation of the client interface.

Main responsibilities:
- create and configure the OpenAI client,
- send generation requests,
- return normalized response objects.

Key functions and methods:
- `__init__`
- `_get_client`
- `generate`

### `__init__.py`
Backend selection and public client entrypoint.

Main responsibilities:
- resolve the active backend,
- expose `get_llm_client()` to callers,
- keep higher-level code agnostic to the concrete provider.

Key functions:
- `_get_openai_client`
- `get_llm_client`

## Dependency flow

This package is used by:

- `src.generate.synthetic_lr`
- `src.evaluate.llm_judge`
- `src.evaluate.run_evaluation`
- `src.normalize.run_synthetic_lr_batch`
- `src.normalize.run_synthetic_lr_lane`

It depends on:

- backend-specific SDKs, currently OpenAI,
- environment variables such as API keys and model names.

## What to inspect first

If you are debugging model calls, inspect these files in order:

1. `__init__.py`
2. `base.py`
3. `openai_client.py`
4. the caller that constructs `GenerationRequest`

## Commands

Inspect public functions:

```bash
grep -R "def get_llm_client\|def generate\|class GenerationRequest" -n src/llm_client src/generate src/evaluate src/normalize
```

Run client tests:

```bash
pytest -q tests/test_llm_client.py tests/test_openai_client.py
```

## Notes

- This package is intentionally thin and should stay provider-agnostic.
- If a new backend is added later, document it here and keep the request/response contract stable.
- When changing request fields or response metadata, update the evaluate and generate docs too.
