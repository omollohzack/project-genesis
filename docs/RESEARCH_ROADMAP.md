# Research and Engineering Roadmap

## Alpha — bounded proof of architecture
- One bounded simulated environment.
- Five persistent inhabitants: Ari, Bela, Cato, Dara, Eli.
- Event-driven world loop and deterministic state validation.
- Agent-scoped persistent memory.
- Provider-independent inference contract with a no-cost stub.
- Unit tests for world transitions and memory privacy.
- First controlled collaboration experiment.

## Beta — measured collaboration
Add communication, relationships, shared knowledge with provenance, an experiment runner, deterministic seeds, scoring, and optional provider adapters behind budgets. Compare independent agents, communication-only agents, and communication-plus-memory agents.

## Expansion — evidence-led scale
Increase agent counts only after profiling CPU, memory, storage, inference volume, and experiment quality. Add PostgreSQL, vector retrieval, background workers, or distributed services only when a measured bottleneck requires them.

## Acceptance principles
Tests pass; behaviour is reproducible; private memory isolation is enforced; inference is budgeted and attributable; candidate discoveries are independently evaluated; changes are reversible.
