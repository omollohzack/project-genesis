from genesis.inference.base import InferenceRequest, StubProvider


def test_stub_provider_has_no_external_dependency():
    result = StubProvider().generate(
        InferenceRequest(agent_id="ari", task="classify", prompt="A short prompt")
    )
    assert result.provider == "stub"
    assert result.text.startswith("[stub response")
