import json

import pytest

from genesis.inference.base import InferenceRequest
from genesis.inference.ollama import (
    OllamaError,
    OllamaHTTPError,
    OllamaProvider,
    OllamaUnavailableError,
)

SUCCESS_BODY = json.dumps({
    "model": "llama3",
    "message": {"role": "assistant", "content": "A considered answer."},
    "prompt_eval_count": 11,
    "eval_count": 3,
}).encode("utf-8")


class FakeTransport:
    """Records the outgoing request and replies with a canned response."""

    def __init__(self, status=200, headers=None, body=SUCCESS_BODY):
        self.status = status
        self.headers = headers or {}
        self.body = body
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append((request, timeout))
        return self.status, self.headers, self.body


def make_provider(transport, **kwargs):
    return OllamaProvider(transport=transport, **kwargs)


def sample_request():
    return InferenceRequest(agent_id="ari", task="reason", prompt="What should I do next?")


def test_ollama_success_maps_response_and_request():
    transport = FakeTransport()
    provider = make_provider(transport, timeout=12.5)

    result = provider.generate(sample_request())

    assert result.provider == "ollama"
    assert result.model == "llama3"
    assert result.text == "A considered answer."
    assert result.input_tokens == 11
    assert result.output_tokens == 3

    (sent_request, sent_timeout), = transport.requests
    assert sent_timeout == 12.5
    assert sent_request.full_url == "http://localhost:11434/api/chat"
    # A local daemon needs no credentials; none must be sent.
    assert sent_request.get_header("Authorization") is None
    payload = json.loads(sent_request.data.decode("utf-8"))
    assert payload["model"] == provider.model
    assert payload["messages"] == [{"role": "user", "content": "What should I do next?"}]
    assert payload["stream"] is False
    assert payload["options"] == {"num_predict": 250}


def test_ollama_disables_think_mode_so_reasoning_models_answer():
    # Reasoning models (e.g. qwen3.5) otherwise spend the whole output
    # budget on hidden thinking and return an empty message.
    transport = FakeTransport()
    make_provider(transport).generate(sample_request())

    (sent_request, _), = transport.requests
    payload = json.loads(sent_request.data.decode("utf-8"))
    assert payload["think"] is False


def test_ollama_reads_model_and_host_from_environment():
    provider = OllamaProvider(
        environ={"GENESIS_OLLAMA_MODEL": "qwen3.5:2b", "OLLAMA_HOST": "http://100.121.170.117:11434"},
        transport=FakeTransport(),
    )
    assert provider.model == "qwen3.5:2b"
    assert provider.base_url == "http://100.121.170.117:11434"


def test_ollama_http_error_includes_status_and_detail():
    body = json.dumps({"error": "model 'nope' not found"}).encode("utf-8")
    provider = make_provider(FakeTransport(status=404, body=body))

    with pytest.raises(OllamaHTTPError) as caught:
        provider.generate(sample_request())
    assert caught.value.status == 404
    assert "model 'nope' not found" in str(caught.value)


def test_ollama_malformed_body_raises_adapter_error():
    provider = make_provider(FakeTransport(body=b"not json"))
    with pytest.raises(OllamaError, match="malformed"):
        provider.generate(sample_request())


def test_ollama_empty_response_raises_adapter_error():
    body = json.dumps({
        "model": "qwen3.5:2b",
        "message": {"role": "assistant", "content": "  "},
        "prompt_eval_count": 9,
        "eval_count": 140,
    }).encode("utf-8")
    provider = make_provider(FakeTransport(body=body))
    with pytest.raises(OllamaError, match="empty"):
        provider.generate(sample_request())


def test_ollama_unavailable_error_propagates():
    def down_transport(request, timeout):
        raise OllamaUnavailableError("Cannot reach the Ollama daemon")

    provider = make_provider(down_transport)
    with pytest.raises(OllamaUnavailableError):
        provider.generate(sample_request())


def test_ollama_rejects_invalid_configuration_and_tier():
    with pytest.raises(ValueError, match="timeout"):
        OllamaProvider(timeout=0, transport=FakeTransport())
    with pytest.raises(ValueError, match="model"):
        OllamaProvider(model="  ", transport=FakeTransport())
    provider = make_provider(FakeTransport())
    with pytest.raises(ValueError, match="tier"):
        provider.generate(InferenceRequest(agent_id="ari", task="reason", prompt="Hi", tier=9))
