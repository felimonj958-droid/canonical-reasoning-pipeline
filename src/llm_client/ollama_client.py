"""
Ollama backend for the LLMClient protocol.

Wraps the local Ollama generation logic behind the provider-agnostic
LLMClient interface. The `ollama` package is imported lazily so this
module is importable without it — unit tests and API-only environments
never need the dependency.
"""

from __future__ import annotations

import time
from typing import Optional

from .base import GenerationRequest, GenerationResponse


class OllamaClient:
    """Local Ollama backend."""

    backend_name = "ollama"

    def __init__(self, default_model: str = "qwen3:8b", host: Optional[str] = None):
        self.default_model = default_model
        self.host = host  # e.g. "http://localhost:11434"; None = library default
        self._client = None  # cached lazily on first _get_client()

    def _get_client(self):
        """Import ollama lazily so this file is importable without it.

        The client handle is cached on the instance so repeated calls
        to generate() reuse the same underlying HTTP client.
        """
        if self._client is not None:
            return self._client

        try:
            import ollama  # noqa: WPS433 — deliberate lazy import
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "The 'ollama' package is required to use OllamaClient. "
                "Install it with `pip install ollama`, or set LLM_BACKEND "
                "to a different backend."
            ) from exc

        self._client = ollama.Client(host=self.host) if self.host else ollama
        return self._client

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        client = self._get_client()
        model = request.model or self.default_model

        messages = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        messages.append({"role": "user", "content": request.prompt})

        options = {
            "temperature": request.temperature,
            "num_predict": request.max_tokens,
        }
        options.update(request.extra or {})

        started = time.perf_counter()
        response = client.chat(
            model=model,
            messages=messages,
            options=options,
        )
        elapsed = time.perf_counter() - started

        text = response["message"]["content"]

        return GenerationResponse(
            text=text,
            backend=self.backend_name,
            model=model,
            prompt_tokens=response.get("prompt_eval_count"),
            completion_tokens=response.get("eval_count"),
            latency_seconds=elapsed,
            raw=dict(response) if isinstance(response, dict) else None,
        )