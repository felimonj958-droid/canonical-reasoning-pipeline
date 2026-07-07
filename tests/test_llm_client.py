from src.generate.synthetic_lr import DEFAULT_PROMPT_VERSION
from src.generate.synthetic_lr import generate_synthetic_lr
from src.llm_client.base import GenerationRequest, GenerationResponse


class FakeClient:
    backend_name = "fake"
    default_model = "fake-model-v0"

    def __init__(self):
        self.calls = []

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        self.calls.append(request)
        return GenerationResponse(
            text=(
                "Stimulus:\n"
                "A short argument.\n\n"
                "Question:\n"
                "Which one of the following most accurately describes a flaw in the argument?\n\n"
                "Choices:\n"
                "A. first\n"
                "B. second\n"
                "C. third\n"
                "D. fourth\n"
                "E. fifth\n\n"
                "Correct: A\n"
            ),
            backend=self.backend_name,
            model=self.default_model,
            prompt_tokens=42,
            completion_tokens=99,
            latency_seconds=0.01,
        )


def test_synthetic_lr_uses_injected_client():
    client = FakeClient()
    text, meta = generate_synthetic_lr(
        flaw_type="causal",
        difficulty="easy",
        client=client,
    )

    assert client.calls, "client.generate was not called"
    assert text.startswith("Stimulus:")
    assert meta.backend == "fake"
    assert meta.model == "fake-model-v0"
    assert meta.flaw_type == "causal"
    assert meta.difficulty == "easy"
    assert meta.prompt_version == DEFAULT_PROMPT_VERSION
    assert meta.prompt_tokens == 42
    assert meta.completion_tokens == 99