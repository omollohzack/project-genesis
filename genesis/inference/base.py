"""Minimal provider adapter interface and deterministic stub."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class InferenceRequest:
    agent_id: str
    task: str
    prompt: str
    tier: int = 1
    max_output_tokens: int = 250


@dataclass(frozen=True)
class InferenceResponse:
    text: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int


class InferenceProvider(Protocol):
    def generate(self, request: InferenceRequest) -> InferenceResponse: ...


class StubProvider:
    """No-cost deterministic placeholder; not an intelligent model."""

    def generate(self, request: InferenceRequest) -> InferenceResponse:
        if request.tier not in (0, 1, 2, 3):
            raise ValueError("tier must be between 0 and 3")
        return InferenceResponse(
            text=f"[stub response for {request.task}]",
            provider="stub",
            model="deterministic-stub-v1",
            input_tokens=len(request.prompt.split()),
            output_tokens=5,
        )
