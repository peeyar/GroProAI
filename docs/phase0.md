# Phase 0 design notes — engine on stub metadata

## How metadata flows
1. `Settings.from_env()` picks the context dir: `model-context/stub/` when `MOCK_PBI=1`,
   `model-context/` otherwise (`MODEL_CONTEXT_DIR` overrides).
2. `app.metadata.tmdl` reads table/column/measure **names** from the TMDL — expressions
   are never interpreted; Power BI stays the only calculation engine.
3. `app.metadata.loader` merges `model-map.json` with the TMDL into a `ModelContext`:
   bridge bucket bindings, drill hierarchy, periods, the DAX identifier allowlist, and
   the glossary. Every schema name in the map is validated against the TMDL at startup,
   so a typo fails at boot, not in a CEO-facing query.
4. `app.metadata.context.build_chat_context` renders the chat system prompt from the
   same object — the LLM only ever sees allowlisted names.

## Fixtures are self-describing
Each file in `fixtures/` carries its own spec (`kind`, `flavor`, `level`, `path`) plus
the result rows. `scripts/onboard_model.py --stub` rebuilds `fixtures/index.json` by
running each spec through `app.powerbi.queries` and recording the DAX; the mock client
then serves fixtures keyed by `sha256(normalized DAX)` — the same cache key the live
client will use in Phase 1. A test asserts the index always matches the builders, so
query builders and fixtures cannot drift apart silently.

## Onboarding the real model
`scripts/onboard_model.py --pbip <export>` ingests the TMDL, drafts `model-map.json`
(LLM via `ANTHROPIC_MODEL`, keyword heuristic as fallback — unresolved slots are
`REVIEW-ME`, which fail validation until Raj resolves them), pauses for review, runs
the grain check, and captures fixtures by walking the drill chain live.
`scripts/grain_check.py` walks bu → customer → product → item with real queries and
exits 2 with a STOP report if item-level rows are missing — that fix is Raj's call.

## Deliberately deferred
- Live Power BI client (MSAL, 40 q/min rate limit, 429 backoff, cache): Phase 1.
- `/api/bridge`, `/api/drill`, `/api/freshness`: Phase 1.
- TOPN injection + query logging on LLM-generated DAX: Phase 3 (shape check and
  identifier allowlist already live in `app.dax`).
- DAX `INFO` function self-discovery test: Phase 1, needs the live endpoint.
