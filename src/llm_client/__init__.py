"""
Public entrypoints and factory for llm_client backends.

The factory reads `LLM_BACKEND` from the environment and returns a
concrete `LLMClient`. Callers should never instantiate backends
directly outside of tests.
"""

from __future__ import annotations

import os
from typing import Optional

from .base import GenerationRequest, GenerationResponse, LLMClient
from .ollama_client import OllamaClient
from .openai_client import OpenAIClient

__all__ = [
    "GenerationRequest",
    "GenerationResponse",
    "LLMClient",
    "OllamaClient",
    "OpenAIClient",
    "get_llm_client",
]


def get_llm_client(backend: Optional[str] = None) -> LLMClient:
    """Return an LLMClient based on `backend` or the LLM_BACKEND env var.

    Defaults to Ollama when no backend is specified. Additional backends
    (anthropic, together, deepseek, ...) can be registered here as they
    land.

    Env vars:
        LLM_BACKEND       "ollama" (default) or "openai"
        OLLAMA_MODEL      default model for Ollama (default: qwen3:8b)
        OLLAMA_HOST       optional Ollama host URL
        OPENAI_MODEL      default model for OpenAI (default: gpt-4o-mini)
        OPENAI_API_KEY    OpenAI API key (required for openai backend)
        OPENAI_BASE_URL   optional; use to target OpenAI-compatible APIs
    """

    resolved = (backend or os.environ.get("LLM_BACKEND", "ollama")).lower().strip()

    if resolved == "ollama":
        model = os.environ.get("OLLAMA_MODEL", "qwen3:8b")
        host = os.environ.get("OLLAMA_HOST") or None
        return OllamaClient(default_model=model, host=host)

    if resolved == "openai":
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        return OpenAIClient(default_model=model)

    raise ValueError(
        f"Unknown LLM backend: {resolved!r}. "
        f"Supported backends: 'ollama', 'openai'. "
        f"Additional API backends (anthropic, together, ...) are planned."
    )