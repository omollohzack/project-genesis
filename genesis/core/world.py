"""Deterministic world-state transitions."""

from uuid import uuid4

from genesis.core.models import Agent, World, WorldEvent


class WorldError(ValueError):
    """Raised when a proposed world transition is invalid."""


def add_agent(world: World, agent: Agent) -> None:
    if agent.agent_id in world.agents:
        raise WorldError(f"Agent already exists: {agent.agent_id}")
    world.agents[agent.agent_id] = agent


def advance_tick(world: World, steps: int = 1) -> WorldEvent:
    if steps != 1:
        raise WorldError("Alpha advances exactly one tick per call")
    world.tick += 1
    event = WorldEvent(
        event_id=str(uuid4()),
        tick=world.tick,
        event_type="world.tick",
        actor_id=None,
        payload={},
    )
    world.events.append(event)
    return event


def record_agent_event(
    world: World, actor_id: str, event_type: str, payload: dict | None = None
) -> WorldEvent:
    if actor_id not in world.agents:
        raise WorldError(f"Unknown agent: {actor_id}")
    if not event_type.strip():
        raise WorldError("event_type cannot be empty")
    event = WorldEvent(
        event_id=str(uuid4()),
        tick=world.tick,
        event_type=event_type,
        actor_id=actor_id,
        payload=payload or {},
    )
    world.events.append(event)
    return event
