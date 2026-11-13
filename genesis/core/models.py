"""Small, provider-independent domain models."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Agent:
    agent_id: str
    name: str
    role: str
    goals: list[str] = field(default_factory=list)
    beliefs: dict[str, Any] = field(default_factory=dict)
    status: str = "active"


@dataclass
class WorldEvent:
    event_id: str
    tick: int
    event_type: str
    actor_id: str | None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class World:
    world_id: str
    name: str
    tick: int = 0
    agents: dict[str, Agent] = field(default_factory=dict)
    events: list[WorldEvent] = field(default_factory=list)
