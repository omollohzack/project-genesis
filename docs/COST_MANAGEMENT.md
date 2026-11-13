# Inference Cost Management

## Event-triggered reasoning
Do not call a model for routine movement, arithmetic, resource updates, or ordinary clock ticks. Trigger inference only for meaningful events: ambiguous observations, nontrivial messages, novel planning, unresolved conflicts, or explicitly scheduled research tasks.

## Tier routing
- L0: deterministic code; no model call.
- L1: lightweight interpretation.
- L2: advanced reasoning for complex or novel tasks.
- L3: research-grade reasoning only with explicit authorization.

## Context and token ceilings
Construct prompts progressively: identity and task, current state, relevant recent events, retrieved memories, and shared knowledge only as needed. Initial engineering ceilings:

| Tier | Input ceiling | Output ceiling |
|---|---:|---:|
| L1 | 1,000 tokens | 250 tokens |
| L2 | 4,000 tokens | 800 tokens |
| L3 | 8,000 tokens | 1,500 tokens |

Retrieve fewer records or summarize older history when context is too large, retaining links to original evidence. Never silently discard critical evidence.

## Caching
Start with exact caching keyed by provider, model version, prompt version, normalized task, and context version. Do not reuse private or individualized outputs across agents. Invalidate when relevant world state, memory, prompt, model, or policy versions change. Never treat an unverified cached answer as a verified fact. Defer semantic caching until equivalence checks are reliable.

## Budgets and controls
Enforce limits at global, provider, tier, agent, and experiment levels. Support daily and monthly ceilings, configurable alerts, and hard stops for nonessential paid inference. When a budget is exhausted, deterministic simulation continues; noncritical inference is queued or rejected rather than silently spending more.

## Usage ledger
Record request ID, timestamp, agent, world, experiment, tier, provider/model/version, prompt version, input/output/cached tokens, latency, status, retries, budget decision, and estimated/actual cost. Avoid storing secrets or unnecessary raw private prompts.

Calculate cost from the provider's effective rate card, including distinct input, output, and cached-token rates. Version rate cards by effective date and currency; reconcile estimates against invoices.

## Monthly operating review
Track spend to date, projected month-end, cost by provider/model/agent/tier/experiment, cache hit rate, budget utilization, failed/retried calls, and cost per completed task or independently verified result. Include hosting, storage, backups, monitoring, domains, taxes, and currency conversion in total operating expenses.

Alpha uses the stub provider by default. Enable paid inference only after rate cards, budget policy, usage ledger, and alerts are implemented. No provider prices are assumed here.
