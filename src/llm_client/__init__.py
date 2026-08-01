"""Public entrypoints and factory for llm_client backends.

The factory reads `LLM_BACKEND` from the environment and returns a
concrete `LLMClient`. Callers should never instantiate backends
directly outside of tests.
"""

from __future__ import annotations

import os
from typing import Optional

from .base import GenerationRequest, GenerationResponse, LLMClient
from .openai_client import OpenAIClient

__all__ = [
    "GenerationRequest",
    "GenerationResponse",
    "LLMClient",
    "OpenAIClient",
    "get_llm_client",
]


def _get_openai_client() -> LLMClient:
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    return OpenAIClient(default_model=model)


def get_llm_client(backend: Optional[str] = None) -> LLMClient:
    """Return an LLMClient based on `backend` or the LLM_BACKEND env var.

    Defaults to OpenAI when no backend is specified.

    Env vars:
        LLM_BACKEND     "openai" (default)
        OPENAI_MODEL    default model for OpenAI (default: gpt-4o-mini)
        OPENAI_API_KEY  OpenAI API key (required for openai backend)
        OPENAI_BASE_URL optional; use to target OpenAI-compatible APIs
    """
    resolved = (backend or os.environ.get("LLM_BACKEND", "openai")).lower().strip()

    if resolved == "openai":
        return _get_openai_client()

    raise ValueError(
        f"Unknown LLM backend: {resolved!r}. "
        f"Supported backends: 'openai'."
    )
