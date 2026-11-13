# System Architecture — Alpha

## Architectural choice

Alpha is a **modular monolith**. It has clear internal boundaries but runs as one Python application. Distributed services are deferred until measured scale or reliability requirements justify them.

## Modules

- **World engine:** authoritative world state, simulation clock, resources, events, and transition validation.
- **Agent runtime:** lifecycle, perception, cognition routing, action proposals, and scheduling.
- **Identity and memory:** durable agent profiles and owner-scoped episodic, semantic, procedural, social, and identity memory.
- **Civilization systems:** communication, relationships, cooperation, and shared institutions.
- **Human interface:** observation, participation, and governance controls.
- **Observation engine:** event capture, context reconstruction, and provenance.
- **Intelligence distillation:** candidate concepts, patterns, strategies, and hypotheses.
- **Research and verification:** experiments, baselines, replication, scoring, and evidence records.
- **Evolution and governance:** isolated proposals, review, approval, deployment, audit, and rollback.

## Hybrid inference

The world engine remains authoritative. Model outputs are untrusted proposals; the engine validates every state-changing action.

| Tier | Intended use | Default handling |
|---|---|---|
| L0 | Rules, arithmetic, routine state updates | Deterministic code |
| L1 | Basic interpretation and classification | Lightweight inference |
| L2 | Novel problems and complex reasoning | Advanced inference |
| L3 | Explicitly authorized research tasks | Research-grade inference |

Inference is event-triggered, not a continuous per-agent loop. Provider adapters must support structured outputs, timeouts, retries, token ceilings, budget checks, cost attribution, and safe fallback.

## Memory and knowledge

Private memories are keyed to one agent and retrieved only through owner-scoped APIs. Shared knowledge is a separate store with explicit sharing and provenance. Each claim records whether it is an observation, interpretation, belief, hypothesis, or verified claim. Summaries assist retrieval but never replace source events or evidence.

## Alpha data concepts

Worlds, snapshots, agents, memories, relationships, beliefs, goals, events, actions, knowledge claims, evidence, experiments, experiment runs, inference requests, cost records, development proposals, and audit records.

## Trust boundaries

- Agents see only information available to them.
- No agent can directly edit another agent's identity or private memory.
- No unrestricted network access or arbitrary code execution by default.
- Model responses never bypass world validation.
- Self-modification is staged and human-approved.
