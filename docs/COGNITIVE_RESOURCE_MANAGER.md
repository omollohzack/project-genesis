# Cognitive Resource Manager (Alpha)

## Purpose
Prevent uncontrolled inference loops and make model usage measurable. The manager is provider-independent and receives a provider implementing the existing InferenceProvider protocol.

## Controls
- Tier-specific approximate input and output limits.
- Per-agent daily request and USD budget checks.
- Exact response caching keyed by agent, task, prompt, tier, output limit, provider, model, and prompt version.
- Usage ledger records successful calls, cache hits, and failures.
- Cost estimates use caller-supplied USD rates per million tokens. Keep rate cards current and version them outside this initial component.

## Safety and accounting limits
- TokenEstimator is a rough UTF-8 byte approximation, not a provider tokenizer.
- Budget preflight uses estimated input and maximum requested output; provider-reported actual usage is recorded after the call.
- A cache hit is scoped to the requesting agent and prompt/model versions; no cross-agent private-context reuse.
- Failed requests are logged with zero recorded cost because provider billing after a transport failure cannot be inferred. Reconcile actual billing against provider invoices.
- This initial SQLite ledger is a prototype. It does not coordinate budgets across multiple processes, machines, or concurrent requests. Production requires atomic reservations and shared transactional storage.
- Rates are not embedded; no provider pricing is assumed. Paid inference should remain disabled until current rates and a hard budget are configured.
