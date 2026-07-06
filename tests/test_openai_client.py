"""Unit tests for OpenAIClient using a fully mocked SDK."""

from __future__ import annotations

import sys
import types

import pytest

from src.llm_client.base import GenerationRequest


class _FakeUsage:
    def __init__(self, prompt_tokens, completion_tokens):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content, model, prompt_tokens=17, completion_tokens=42):
        self.choices = [_FakeChoice(content)]
        self.model = model
        self.usage = _FakeUsage(prompt_tokens, completion_tokens)


class _FakeCompletions:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeResponse(
            content="A synthetic LR item.",
            model=kwargs.get("model", "gpt-4o-mini"),
        )


class _FakeChat:
    def __init__(self):
        self.completions = _FakeCompletions()


class _FakeOpenAI:
    def __init__(self, api_key=None, base_url=None, timeout=None):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.chat = _FakeChat()


@pytest.fixture
def fake_openai_module(monkeypatch):
    """Install a fake `openai` module so the lazy import inside the client hits it."""
    module = types.ModuleType("openai")
    module.OpenAI = _FakeOpenAI
    monkeypatch.setitem(sys.modules, "openai", module)
    return module


def test_openai_client_generates_and_records_metadata(fake_openai_module, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")

    # Import AFTER the fake module is in place so the lazy import works
    from src.llm_client.openai_client import OpenAIClient

    client = OpenAIClient(default_model="gpt-4o-mini")

    request = GenerationRequest(
        prompt="write a synthetic LR item",
        model="",  # empty -> client uses default_model
        temperature=0.5,
        max_tokens=256,
        system="You are an expert LSAT writer.",
    )
    response = client.generate(request)

    assert response.backend == "openai"
    assert response.model == "gpt-4o-mini"
    assert response.text == "A synthetic LR item."
    assert response.prompt_tokens == 17
    assert response.completion_tokens == 42
    assert response.latency_seconds is not None and response.latency_seconds >= 0


def test_openai_client_forwards_call_parameters(fake_openai_module, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")

    from src.llm_client.openai_client import OpenAIClient

    client = OpenAIClient(default_model="gpt-4o-mini")

    request = GenerationRequest(
        prompt="hello",
        model="gpt-4o",
        temperature=0.9,
        max_tokens=128,
        system="sys",
        extra={"top_p": 0.95},
    )
    client.generate(request)

    # Reach into the fake SDK to inspect the call payload
    fake_client = client._get_client()
    calls = fake_client.chat.completions.calls
    assert len(calls) >= 1
    last = calls[-1]

    assert last["model"] == "gpt-4o"
    assert last["temperature"] == 0.9
    assert last["max_tokens"] == 128
    assert last["top_p"] == 0.95
    assert last["messages"][0]["role"] == "system"
    assert last["messages"][0]["content"] == "sys"
    assert last["messages"][1]["role"] == "user"
    assert last["messages"][1]["content"] == "hello"


def test_openai_client_raises_when_api_key_missing(fake_openai_module, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    from src.llm_client.openai_client import OpenAIClient

    client = OpenAIClient(default_model="gpt-4o-mini")
    request = GenerationRequest(prompt="x", model="", temperature=0.0, max_tokens=1)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        client.generate(request)


def test_factory_returns_openai_client_when_env_set(fake_openai_module, monkeypatch):
    monkeypatch.setenv("LLM_BACKEND", "openai")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")

    from src.llm_client import get_llm_client
    from src.llm_client.openai_client import OpenAIClient

    client = get_llm_client()
    assert isinstance(client, OpenAIClient)
    assert client.default_model == "gpt-4o"