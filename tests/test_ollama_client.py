from src.llm_client.base import GenerationRequest
from src.llm_client.ollama_client import OllamaClient


class DummyClient:
    def __init__(self):
        self.calls = []

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "message": {"content": "ok"},
            "prompt_eval_count": 1,
            "eval_count": 1,
        }


def test_ollama_client_disables_thinking(monkeypatch):
    dummy = DummyClient()

    def fake_get_client(self):
        return dummy

    monkeypatch.setattr(OllamaClient, "_get_client", fake_get_client)

    client = OllamaClient(default_model="qwen3:8b")
    req = GenerationRequest(prompt="hello", temperature=0.7, max_tokens=32)

    client.generate(req)

    assert dummy.calls[0]["options"]["think"] is False
