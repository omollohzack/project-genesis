import pytest

from genesis.inference.base import InferenceRequest, InferenceResponse
from genesis.inference.resources import (BudgetDenied, BudgetPolicy, CognitiveResourceManager,
    ExactResponseCache, TierLimit, TokenEstimator, UsageLedger, CostCalculator)


class CountingProvider:
    def __init__(self):
        self.calls = 0

    def generate(self, request):
        self.calls += 1
        return InferenceResponse("result", "test", "test-model", 10, 2)


def setup_manager(tmp_path, budget=1.0):
    db = tmp_path / "resources.db"
    ledger = UsageLedger(db)
    cache = ExactResponseCache(db)
    policy = BudgetPolicy(daily_budget_usd=budget, max_daily_requests=10)
    return CognitiveResourceManager(ledger, cache, policy), ledger


def test_token_estimator_and_cost_calculator():
    assert TokenEstimator.estimate("") == 0
    assert TokenEstimator.estimate("abcd") == 1
    assert CostCalculator.calculate(1_000_000, 500_000, 1.0, 2.0) == 2.0


def test_exact_cache_prevents_duplicate_provider_call(tmp_path):
    manager, ledger = setup_manager(tmp_path)
    provider = CountingProvider()
    request = InferenceRequest("ari", "summarize", "same prompt", tier=1, max_output_tokens=20)
    first = manager.generate(request, provider, "test", "test-model", "p1", 1.0, 1.0)
    second = manager.generate(request, provider, "test", "test-model", "p1", 1.0, 1.0)
    assert first == second
    assert provider.calls == 1
    assert ledger.daily_totals("ari")[0] == 2
    assert ledger.list_recent()[0]["cache_hit"] == 1


def test_cache_isolated_by_agent_and_prompt_version(tmp_path):
    manager, _ = setup_manager(tmp_path)
    provider = CountingProvider()
    request = InferenceRequest("ari", "summarize", "same prompt", tier=1, max_output_tokens=20)
    manager.generate(request, provider, "test", "test-model", "p1")
    manager.generate(InferenceRequest("bela", "summarize", "same prompt", tier=1, max_output_tokens=20), provider, "test", "test-model", "p1")
    manager.generate(request, provider, "test", "test-model", "p2")
    assert provider.calls == 3


def test_tier_limits_deny_oversized_request(tmp_path):
    manager, _ = setup_manager(tmp_path)
    request = InferenceRequest("ari", "reason", "x" * 5000, tier=1, max_output_tokens=20)
    with pytest.raises(BudgetDenied):
        manager.generate(request, CountingProvider(), "test", "model", "p1")


def test_daily_budget_denies_request_before_provider_call(tmp_path):
    manager, _ = setup_manager(tmp_path, budget=0.000001)
    provider = CountingProvider()
    request = InferenceRequest("ari", "reason", "small prompt", tier=1, max_output_tokens=20)
    with pytest.raises(BudgetDenied):
        manager.generate(request, provider, "test", "model", "p1", 100.0, 100.0)
    assert provider.calls == 0


def test_cache_does_not_cross_agents(tmp_path):
    manager, _ = setup_manager(tmp_path)
    provider = CountingProvider()
    req = InferenceRequest("ari", "task", "context", tier=1, max_output_tokens=20)
    manager.generate(req, provider, "test", "model", "v1")
    manager.generate(InferenceRequest("bela", "task", "context", tier=1, max_output_tokens=20), provider, "test", "model", "v1")
    assert provider.calls == 2
