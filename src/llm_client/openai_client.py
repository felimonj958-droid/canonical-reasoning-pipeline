"""
OpenAI backend for the LLMClient protocol.

Uses the official `openai` Python SDK's Chat Completions API. The SDK
is imported lazily so this module stays importable in environments
that only use other backends (or none). Authentication is picked up
from the OPENAI_API_KEY environment variable by the SDK itself.
"""

from __future__ import annotations

import os
import time
from typing import Optional

from .base import GenerationRequest, GenerationResponse


class OpenAIClient:
    """OpenAI Chat Completions backend."""

    backend_name = "openai"

    def __init__(
        self,
        default_model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
    ):
        self.default_model = default_model
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._base_url = base_url or os.environ.get("OPENAI_BASE_URL")
        self._timeout = timeout
        self._client = None  # cached lazily on first _get_client()

    def _get_client(self):
        """Import openai lazily so this file is importable without it.

        The SDK client is cached on the instance so repeated calls to
        generate() reuse the same underlying HTTP client.
        """
        if self._client is not None:
            return self._client

        try:
            from openai import OpenAI  # noqa: WPS433 — deliberate lazy import
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "The 'openai' package is required to use OpenAIClient. "
                "Install it with `pip install openai`, or set LLM_BACKEND "
                "to a different backend."
            ) from exc

        if not self._api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Export it in the environment "
                "or pass api_key= when constructing OpenAIClient."
            )

        self._client = OpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
            timeout=self._timeout,
        )
        return self._client

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        client = self._get_client()
        model = request.model or self.default_model

        messages = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        messages.append({"role": "user", "content": request.prompt})

        call_kwargs = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        call_kwargs.update(request.extra or {})

        started = time.perf_counter()
        response = client.chat.completions.create(**call_kwargs)
        elapsed = time.perf_counter() - started

        text = response.choices[0].message.content or ""

        usage = getattr(response, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", None) if usage else None
        completion_tokens = getattr(usage, "completion_tokens", None) if usage else None

        served_model = getattr(response, "model", model) or model

        return GenerationResponse(
            text=text,
            backend=self.backend_name,
            model=served_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_seconds=elapsed,
            raw=None,
        )