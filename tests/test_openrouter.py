import json

import pytest

from genesis.inference.base import InferenceRequest
from genesis.inference.openrouter import (
    MissingAPIKeyError,
    OpenRouterError,
    OpenRouterHTTPError,
    OpenRouterProvider,
    RateLimitError,
)

SUCCESS_BODY = json.dumps({
    "model": "meta-llama/llama-3.3-70b-instruct:free",
    "choices": [{"message": {"role": "assistant", "content": "A considered answer."}}],
    "usage": {"prompt_tokens": 11, "completion_tokens": 3},
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
    kwargs.setdefault("api_key", "test-key")
    return OpenRouterProvider(transport=transport, **kwargs)


def sample_request():
    return InferenceRequest(agent_id="ari", task="reason", prompt="What should I do next?")


def test_openrouter_success_maps_response_and_request():
    transport = FakeTransport()
    provider = make_provider(transport, timeout=12.5)

    result = provider.generate(sample_request())

    assert result.provider == "openrouter"
    assert result.model == "meta-llama/llama-3.3-70b-instruct:free"
    assert result.text == "A considered answer."
    assert result.input_tokens == 11
    assert result.output_tokens == 3

    (sent_request, sent_timeout), = transport.requests
    assert sent_timeout == 12.5
    assert sent_request.full_url == "https://openrouter.ai/api/v1/chat/completions"
    assert sent_request.get_header("Authorization") == "Bearer test-key"
    payload = json.loads(sent_request.data.decode("utf-8"))
    assert payload["model"] == provider.model
    assert payload["messages"] == [{"role": "user", "content": "What should I do next?"}]
    assert payload["max_tokens"] == 250


def test_openrouter_missing_api_key_fails_clearly():
    with pytest.raises(MissingAPIKeyError, match="OPENROUTER_API_KEY"):
        OpenRouterProvider(environ={})
    with pytest.raises(MissingAPIKeyError):
        OpenRouterProvider(api_key="  ", environ={})


def test_openrouter_reads_key_and_model_from_environment():
    provider = OpenRouterProvider(
        environ={"OPENROUTER_API_KEY": "env-key", "GENESIS_OPENROUTER_MODEL": "custom/model"},
        transport=FakeTransport(),
    )
    assert provider.model == "custom/model"


def test_openrouter_http_error_includes_status_and_detail():
    body = json.dumps({"error": {"message": "model unavailable"}}).encode("utf-8")
    provider = make_provider(FakeTransport(status=503, body=body))

    with pytest.raises(OpenRouterHTTPError) as caught:
        provider.generate(sample_request())
    assert caught.value.status == 503
    assert "model unavailable" in str(caught.value)


def test_openrouter_rate_limit_raises_with_retry_after():
    body = json.dumps({"error": {"message": "slow down"}}).encode("utf-8")
    transport = FakeTransport(status=429, headers={"Retry-After": "7"}, body=body)
    provider = make_provider(transport)

    with pytest.raises(RateLimitError) as caught:
        provider.generate(sample_request())
    assert caught.value.status == 429
    assert caught.value.retry_after == 7.0


def test_openrouter_malformed_body_raises_adapter_error():
    provider = make_provider(FakeTransport(body=b"not json"))
    with pytest.raises(OpenRouterError, match="malformed"):
        provider.generate(sample_request())


def test_openrouter_rejects_invalid_tier_before_calling():
    transport = FakeTransport()
    provider = make_provider(transport)
    with pytest.raises(ValueError, match="tier"):
        provider.generate(InferenceRequest(agent_id="ari", task="reason", prompt="Hi", tier=9))
    assert transport.requests == []
