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

## Long-range direction — a problem-solving society

Beyond Expansion, the direction of travel is a society of inhabitants that can work a shared problem end to end: one identifies a problem, another researches it, another evaluates resources, another coordinates the response, another monitors whether the solution worked. Candidate domains, in the long term, include agriculture, education, disaster response, healthcare logistics and public services.

This direction is chosen because it runs on primitives Genesis already has, rather than new machinery:

- Coordination is the commitment system (offers, acceptances, withdrawals, fulfilment).
- Accountability is the trust model: refusals and withdrawals are recorded, and refusal never reduces trust.
- Monitoring is durable, agent-scoped memory plus the world's event log.
- Identity survives the model: the inhabitants belong to the world, not the provider, so a society can outlive any single inference backend.

### First evidence step — EXP-002 (gated on EXP-001)

A bounded simulated community problem (for example, coordinating the repair of a shared water point in a fictional settlement), worked by the inhabitants through commitments only. Success criteria are fixed before the run; the run is scored against them; results are published either way.

### Standing rule

This section records a direction, not a capability. No phase begins until the previous phase's evidence is published, and no applied pilot is in scope while the simulation evidence does not exist.
