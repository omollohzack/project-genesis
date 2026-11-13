# Contributing to Project Genesis

## Development setup

Requires Python 3.10 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
python -m genesis
```

The default runtime uses a deterministic stub inference provider. No API key
or paid model is required to run the test suite or the smoke test.

## Rules of the house

These come from the master specification's engineering rules and are not
optional:

1. Write tests alongside implementation. A feature without a test run is a
   claim, not a capability.
2. Never state that tests pass or a feature works unless you have seen the
   run. Report failures exactly as observed.
3. Keep modules small and interfaces documented; use type hints and
   structured validation.
4. Use migrations for database changes; record experiment seeds and
   configuration so runs can be replayed.
5. Never commit secrets, API keys, or local databases. Keep credentials in an
   ignored `.env` file; `.env.example` holds placeholder names only.
6. Treat model outputs and agent-generated content as untrusted input.
7. Make state changes auditable; keep deterministic simulation separate from
   model inference.
8. Document known limitations and failed experiments. Behavioural
   sophistication is not evidence of consciousness, and no change may claim
   otherwise.

## Pull requests

- Work in small, stacked pull requests when a change builds on another;
  say so in the description and merge bottom-up, in dependency order.
- A pull request description must state what was validated, how, and what is
  known to be incomplete.
- CI runs the full test suite and the smoke test on Python 3.10–3.12 for
  every push and pull request. Red CI is a stop, not a suggestion.
