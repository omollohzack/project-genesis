"""Cognitive Resource Manager: budgets, exact caching, and usage accounting."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from genesis.inference.base import InferenceRequest, InferenceResponse, InferenceProvider


class BudgetDenied(RuntimeError):
    """Raised before a request when it exceeds configured resource limits."""


@dataclass(frozen=True)
class TierLimit:
    max_input_tokens: int
    max_output_tokens: int


DEFAULT_TIER_LIMITS = {
    0: TierLimit(500, 100),
    1: TierLimit(1000, 250),
    2: TierLimit(4000, 800),
    3: TierLimit(8000, 1500),
}


class TokenEstimator:
    """Conservative, provider-independent approximation; not a tokenizer."""

    @staticmethod
    def estimate(text: str) -> int:
        if not text:
            return 0
        return max(1, (len(text.encode("utf-8")) + 3) // 4)


class UsageLedger:
    def __init__(self, database: str | Path):
        self.database = str(database)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS inference_usage (
                request_id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, task TEXT NOT NULL,
                tier INTEGER NOT NULL, provider TEXT NOT NULL, model TEXT NOT NULL,
                input_tokens INTEGER NOT NULL, output_tokens INTEGER NOT NULL,
                estimated_cost_usd REAL NOT NULL, status TEXT NOT NULL,
                cache_hit INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_usage_agent_date ON inference_usage(agent_id, created_at)")

    def _connect(self):
        return sqlite3.connect(self.database)

    def record(self, *, agent_id: str, task: str, tier: int, provider: str, model: str,
               input_tokens: int, output_tokens: int, cost_usd: float,
               status: str, cache_hit: bool = False) -> str:
        request_id = str(uuid4())
        with self._connect() as db:
            db.execute("""INSERT INTO inference_usage
                (request_id, agent_id, task, tier, provider, model, input_tokens,
                 output_tokens, estimated_cost_usd, status, cache_hit)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (request_id, agent_id, task, tier, provider, model, input_tokens,
                 output_tokens, cost_usd, status, int(cache_hit)))
        return request_id

    def daily_totals(self, agent_id: str | None = None) -> tuple[int, float]:
        query = "SELECT COUNT(*), COALESCE(SUM(estimated_cost_usd), 0) FROM inference_usage WHERE date(created_at) = date('now') AND status IN ('success', 'cache_hit')"
        params = ()
        if agent_id is not None:
            query += " AND agent_id = ?"
            params = (agent_id,)
        with self._connect() as db:
            count, cost = db.execute(query, params).fetchone()
        return int(count), float(cost)

    def list_recent(self, limit: int = 100) -> list[dict]:
        if limit < 1:
            raise ValueError("limit must be positive")
        with self._connect() as db:
            db.row_factory = sqlite3.Row
            rows = db.execute("SELECT * FROM inference_usage ORDER BY created_at DESC, request_id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]


class ExactResponseCache:
    """Exact cache scoped to agent, model, task, prompt, and prompt version."""

    def __init__(self, database: str | Path):
        self.database = str(database)
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS inference_cache (cache_key TEXT PRIMARY KEY, response_json TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")

    def _connect(self):
        return sqlite3.connect(self.database)

    @staticmethod
    def make_key(request: InferenceRequest, provider: str, model: str, prompt_version: str) -> str:
        material = json.dumps({
            "agent_id": request.agent_id, "task": request.task,
            "prompt": request.prompt, "tier": request.tier,
            "max_output_tokens": request.max_output_tokens,
            "provider": provider, "model": model, "prompt_version": prompt_version,
        }, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    def get(self, key: str) -> InferenceResponse | None:
        with self._connect() as db:
            row = db.execute("SELECT response_json FROM inference_cache WHERE cache_key = ?", (key,)).fetchone()
        if row is None:
            return None
        data = json.loads(row[0])
        return InferenceResponse(**data)

    def put(self, key: str, response: InferenceResponse) -> None:
        payload = json.dumps({
            "text": response.text, "provider": response.provider, "model": response.model,
            "input_tokens": response.input_tokens, "output_tokens": response.output_tokens,
        })
        with self._connect() as db:
            db.execute("INSERT OR REPLACE INTO inference_cache (cache_key, response_json) VALUES (?, ?)", (key, payload))


class CostCalculator:
    """Rates are USD per million tokens; callers must supply current rate-card values."""

    @staticmethod
    def calculate(input_tokens: int, output_tokens: int,
                  input_rate_per_million: float, output_rate_per_million: float) -> float:
        rates = (input_rate_per_million, output_rate_per_million)
        if any(not isinstance(rate, (int, float)) or rate < 0 for rate in rates):
            raise ValueError("Token rates must be non-negative numbers")
        if input_tokens < 0 or output_tokens < 0:
            raise ValueError("Token counts cannot be negative")
        return (input_tokens * input_rate_per_million + output_tokens * output_rate_per_million) / 1_000_000


class BudgetPolicy:
    def __init__(self, daily_budget_usd: float = 1.0, max_daily_requests: int = 100,
                 tier_limits: dict[int, TierLimit] | None = None):
        if daily_budget_usd < 0 or max_daily_requests < 1:
            raise ValueError("Budget must be non-negative and request limit positive")
        self.daily_budget_usd = float(daily_budget_usd)
        self.max_daily_requests = int(max_daily_requests)
        self.tier_limits = dict(tier_limits or DEFAULT_TIER_LIMITS)

    def validate(self, request: InferenceRequest, input_tokens: int) -> None:
        limit = self.tier_limits.get(request.tier)
        if limit is None:
            raise BudgetDenied(f"Unknown inference tier: {request.tier}")
        if input_tokens > limit.max_input_tokens:
            raise BudgetDenied(f"Input estimate exceeds tier {request.tier} limit")
        if request.max_output_tokens > limit.max_output_tokens:
            raise BudgetDenied(f"Output limit exceeds tier {request.tier} limit")


class CognitiveResourceManager:
    def __init__(self, ledger: UsageLedger, cache: ExactResponseCache,
                 policy: BudgetPolicy | None = None):
        self.ledger = ledger
        self.cache = cache
        self.policy = policy or BudgetPolicy()

    def generate(self, request: InferenceRequest, provider: InferenceProvider,
                 provider_name: str, model_name: str, prompt_version: str,
                 input_rate_per_million: float = 0.0,
                 output_rate_per_million: float = 0.0) -> InferenceResponse:
        if not request.agent_id or not request.task or not isinstance(request.prompt, str):
            raise ValueError("Inference request requires agent_id, task, and prompt")
        input_estimate = TokenEstimator.estimate(request.prompt)
        self.policy.validate(request, input_estimate)
        key = self.cache.make_key(request, provider_name, model_name, prompt_version)
        cached = self.cache.get(key)
        if cached is not None:
            self.ledger.record(agent_id=request.agent_id, task=request.task, tier=request.tier,
                provider=provider_name, model=model_name, input_tokens=cached.input_tokens,
                output_tokens=cached.output_tokens, cost_usd=0.0, status="cache_hit", cache_hit=True)
            return cached

        count, spent = self.ledger.daily_totals(request.agent_id)
        if count >= self.policy.max_daily_requests:
            raise BudgetDenied("Agent daily inference request limit reached")
        worst_case = CostCalculator.calculate(input_estimate, request.max_output_tokens,
                                               input_rate_per_million, output_rate_per_million)
        if spent + worst_case > self.policy.daily_budget_usd:
            raise BudgetDenied("Agent daily inference budget would be exceeded")

        started = perf_counter()
        try:
            response = provider.generate(request)
            if not isinstance(response, InferenceResponse):
                raise TypeError("Provider must return InferenceResponse")
            if response.input_tokens < 0 or response.output_tokens < 0:
                raise ValueError("Provider returned invalid token counts")
            if response.output_tokens > request.max_output_tokens:
                raise ValueError("Provider exceeded the requested output-token limit")
            cost = CostCalculator.calculate(response.input_tokens, response.output_tokens,
                                             input_rate_per_million, output_rate_per_million)
            if spent + cost > self.policy.daily_budget_usd:
                raise BudgetDenied("Actual usage exceeded the remaining daily budget")
            self.ledger.record(agent_id=request.agent_id, task=request.task, tier=request.tier,
                provider=provider_name, model=model_name, input_tokens=response.input_tokens,
                output_tokens=response.output_tokens, cost_usd=cost, status="success")
            self.cache.put(key, response)
            return response
        except Exception:
            self.ledger.record(agent_id=request.agent_id, task=request.task, tier=request.tier,
                provider=provider_name, model=model_name, input_tokens=input_estimate,
                output_tokens=0, cost_usd=0.0, status="failed")
            raise
