"""
Provider-agnostic LLM client protocol and message contracts.

This module defines the abstraction that every generation backend
(Ollama, OpenAI, Anthropic, etc.) must implement. Callers depend on
the `LLMClient` protocol, never on a concrete backend.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable


@dataclass(frozen=True)
class GenerationRequest:
    """A single generation request sent to an LLM backend.

    Fields are intentionally minimal and backend-neutral. Backend-specific
    tuning (top_p, stop sequences, etc.) can live in `extra` without
    breaking the protocol.
    """

    prompt: str
    model: str
    temperature: float = 0.7
    max_tokens: int = 1024
    system: Optional[str] = None
    extra: dict = field(default_factory=dict)


@dataclass(frozen=True)
class GenerationResponse:
    """A single generation response returned by an LLM backend.

    `backend` and `model` are captured on the response (not just the
    request) so that downstream canonical records can record which
    backend actually produced the text, independent of what was asked.
    """

    text: str
    backend: str
    model: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    latency_seconds: Optional[float] = None
    raw: Optional[dict] = None


@runtime_checkable
class LLMClient(Protocol):
    """Provider-agnostic LLM client protocol.

    Any backend used by the pipeline must implement `generate` with this
    signature. Backends should be pure with respect to pipeline state:
    they take a request, return a response, and do not touch the
    canonical record, filesystem, or review queues.
    """

    backend_name: str

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        ...