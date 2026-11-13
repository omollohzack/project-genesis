"""Event-driven agent runtime with a replaceable policy boundary.

Policies propose actions; the runtime validates and executes them. The included
policy is deterministic scaffolding, not an LLM or evidence of intelligence.
"""

from dataclasses import dataclass, field
from typing import Protocol

from genesis.core.models import Agent, World
from genesis.core.world import WorldError, record_agent_event
from genesis.memory.store import SQLiteMemoryStore


@dataclass(frozen=True)
class AgentObservation:
    agent_id: str
    tick: int
    world_name: str
    active_agent_ids: tuple[str, ...]
    recent_events: tuple[dict, ...]
    goals: tuple[str, ...]


@dataclass(frozen=True)
class AgentAction:
    action_type: str
    payload: dict = field(default_factory=dict)


class AgentPolicy(Protocol):
    def decide(self, agent: Agent, observation: AgentObservation) -> AgentAction: ...


class ReflectivePolicy:
    """Minimal deterministic policy used until an inference adapter is configured."""

    def decide(self, agent: Agent, observation: AgentObservation) -> AgentAction:
        if not observation.recent_events:
            return AgentAction("wait")
        latest = observation.recent_events[-1]
        return AgentAction(
            "reflect",
            {"text": f"Observed {latest['event_type']} at tick {latest['tick']}."},
        )


class AgentRuntime:
    ALLOWED_ACTIONS = {"wait", "reflect"}

    def __init__(self, memory: SQLiteMemoryStore, policy: AgentPolicy | None = None):
        self.memory = memory
        self.policy = policy or ReflectivePolicy()
        self._last_seen_event: dict[str, str | None] = {}

    def observe(self, world: World, agent_id: str) -> AgentObservation:
        if agent_id not in world.agents:
            raise WorldError(f"Unknown agent: {agent_id}")
        agent = world.agents[agent_id]
        last_id = self._last_seen_event.get(agent_id)
        events = []
        for event in world.events:
            if last_id is None or event.event_id == last_id:
                if last_id is not None:
                    continue
                events.append(event)
            elif events or last_id is None:
                events.append(event)
        # Only expose public world events; private memories are never included.
        return AgentObservation(
            agent_id=agent_id,
            tick=world.tick,
            world_name=world.name,
            active_agent_ids=tuple(sorted(a.agent_id for a in world.agents.values() if a.status == "active")),
            recent_events=tuple(
                {"event_id": e.event_id, "tick": e.tick, "event_type": e.event_type,
                 "actor_id": e.actor_id, "payload": dict(e.payload)}
                for e in events[-20:]
            ),
            goals=tuple(agent.goals),
        )

    def step(self, world: World, agent_id: str) -> AgentAction:
        observation = self.observe(world, agent_id)
        agent = world.agents[agent_id]
        action = self.policy.decide(agent, observation)
        if action.action_type not in self.ALLOWED_ACTIONS:
            raise WorldError(f"Action not permitted in Alpha: {action.action_type}")
        if action.action_type == "reflect":
            text = action.payload.get("text")
            if not isinstance(text, str) or not text.strip():
                raise WorldError("reflect action requires non-empty text")
            self.memory.add(agent_id, "episodic", text.strip(), "runtime_reflection")
            event = record_agent_event(world, agent_id, "agent.reflected", {"text": text.strip()})
            self._last_seen_event[agent_id] = event.event_id
        elif observation.recent_events:
            self._last_seen_event[agent_id] = observation.recent_events[-1]["event_id"]
        return action
