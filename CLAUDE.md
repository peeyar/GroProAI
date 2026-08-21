# CLAUDE.md — GroPro AI (revenue bridge app)

## What this is
CEO-facing web app that replaces the front end of the "GroPro" Power BI monthly revenue
bridge. It answers one question — "Revenue changed. Why?" — with a waterfall, drill-down
to item level, a plain-English narrative, and a chat that can create pinnable charts.
Audience: one non-technical CEO. Bar: instant, polished, never wrong.

## The rule that outranks everything
**Power BI is the only calculation engine.** Never re-implement bridge math in Python or
JS. Every number rendered must come from a DAX query against the published semantic
model. If something can't be produced by DAX, stop and tell Raj — do not approximate.

## Model metadata & onboarding (the .pbix arrives later — design for that)
- The app is **metadata-driven**. At startup the backend loads
  `model-context/model-map.json` plus the TMDL files and builds everything from them:
  the measure/table allowlist, the chat system prompt, the drill hierarchy, and the
  Official View bindings. **No schema names are hardcoded in app code.**
- `model-map.json` is the only schema-aware config (~50 lines): which measures are the
  six bridge buckets and the total, the drill path (BU → customer → product → item),
  and default period filters. The UI builds itself from this file.
- **Until the real .pbix exists:** develop against `model-context/stub/` — stub TMDL,
  stub model-map, and fixtures shaped like GroPro (six buckets, YoY/SEQ, AUTO/HVOR,
  customer/product/region/quarter dims). `MOCK_PBI=1` uses these.
- **When the .pbix arrives (one command):** `scripts/onboard_model.py` — Raj exports
  the pbix as `.pbip` in Power BI Desktop → script ingests the TMDL → LLM drafts the
  real `model-map.json` → Raj reviews and edits → grain check runs → real fixtures are
  captured. The app picks up the new model on restart.
- Optional self-discovery (test in Phase 1): try DAX `INFO` functions (e.g.
  `EVALUATE INFO.MEASURES()`) through executeQueries. If the endpoint supports them,
  the app can pull metadata straight from the Service and the manual TMDL export
  becomes a fallback. Verify first — endpoint docs are inconsistent on INFO support.
- The published dataset in the Service (IDs in `.env`) is the only runtime data
  source. The local pbix is never queried directly.

## Domain glossary
- GroPro = monthly revenue bridge (waterfall / variance walk). Flavors: **YoY** and
  **SEQ** (quarter vs prior quarter). Business units: **AUTO**, **HVOR**.
- Six buckets, which sum to the total change:
  Market (industry volume moved) · Market Mix (our customers vs industry) ·
  Propulsion Mix (gas→EV shift changes $ per vehicle) · Content ($ of parts per
  vehicle) · Price · FX (currency only).
- Upstream data is Excel on SharePoint (Demantra sales, IHS + KGP forecasts, CPV,
  lookup tables). **The app never reads those files in v1** — Power BI refresh owns
  them. We only query the semantic model.

## Repo layout
- `backend/` — FastAPI, Python 3.12: auth, powerbi client, cache, nl2dax, narrative, widgets
- `frontend/` — React + TypeScript + Vite: Official View, My View, chat panel
- `model-context/` — `model-map.json`, TMDL, report layout, `glossary.md`, `stub/`
  (config + reference; app code only writes here via the onboarding script)
- `fixtures/` — captured real query results, used in mock mode
- `docs/` — deeper design notes; reference with @docs/... when needed

## Power BI API facts (do not rediscover these)
- Endpoint: `POST https://api.powerbi.com/v1.0/myorg/groups/{PBI_WORKSPACE_ID}/datasets/{PBI_DATASET_ID}/executeQueries`
- Body: `{"queries":[{"query":"<DAX>"}],"serializerSettings":{"includeNulls":true}}`
- Auth: MSAL client-credentials token, scope `https://analysis.windows.net/powerbi/api/.default`
- Pro limits: **40 queries/min per user**, **100k rows / 1M values per query**, DAX only.
  The client must rate-limit, backoff on HTTP 429, and cache.
- Query style: always aggregate (`SUMMARIZECOLUMNS`, `TOPN`). Never dump a fact table.
  Drill tables paginate with TOPN windows.

## Guardrails on LLM-generated DAX
- Accept only `DEFINE`/`EVALUATE` query syntax; reject anything else before sending.
- Validate every identifier against the allowlist built from `model-context/tmdl/`.
- Inject a `TOPN` cap (default 500 rows) if the query lacks one; 30s server timeout.
- Log every query: user, prompt, DAX, row count, latency.
- Anthropic model name comes from `ANTHROPIC_MODEL` env var — never hardcode one.

## Environment (`.env`, gitignored — never commit)
```
PBI_TENANT_ID=        PBI_CLIENT_ID=        PBI_CLIENT_SECRET=
PBI_WORKSPACE_ID=     PBI_DATASET_ID=
ANTHROPIC_API_KEY=    ANTHROPIC_MODEL=
MOCK_PBI=1
```
- `MOCK_PBI=1` serves `fixtures/` instead of the live API. Default for frontend work.
- Outside-of-code prerequisites (Raj/admin): tenant settings "Dataset Execute Queries
  REST API" and "Allow service principals to use Power BI APIs" enabled; service
  principal added to the workspace. If SP access is blocked, fall back to delegated
  device-code auth for dev.

## UX rules (CEO-grade)
- Opens to the answer: narrative paragraph + waterfall. No filter panes on landing.
- Every number is clickable: bucket → BU → customer → product → item.
- Plain-English tooltips come from `model-context/glossary.md`.
- Cache-first: data changes monthly, so precompute standard views; target <1s
  interactions; cache key = hash of DAX; provide a manual cache-bust endpoint.
- Graceful data states: "August files haven't landed yet — showing July." Never a raw
  error or an empty chart.
- Layout must work at tablet width.

## Build phases (work in order; check off as completed)
- [x] **0 — Engine on stub metadata.** Build the metadata loader (model-map + TMDL →
  allowlist, drill config, chat context), create the GroPro-shaped stub and fixtures,
  and write `scripts/onboard_model.py` + `scripts/grain_check.py` so onboarding the
  real model later is one command. Grain check runs at onboarding: **if item-level
  rows are missing from the model, STOP and report — the fix (adding a detail table
  to the pbix) is Raj's call.**
- [ ] **1 — Backend core.** Auth, powerbi client (limits + cache), `/api/bridge`,
  `/api/drill`, `/api/freshness` stub. Pytest smoke tests run in mock mode.
- [ ] **2 — Official View.** Waterfall, YoY/SEQ toggle, click-drill chain, item table,
  freshness banner.
- [ ] **3 — AI.** `/api/narrative` (auto summary on load) and `/api/chat`
  (NL → DAX → answer + chart spec), both through the guarded query path.
- [ ] **4 — My View.** Pin button on chat/drill charts, per-user widget store,
  react-grid-layout, persisted layouts.

## Widget spec (pinned cards)
`{id, title, dax, chartType: waterfall|bar|line|table, filters, createdFrom: chat|drill}`
stored per user (SQLite). Rendering always goes through the same guarded query path.

## Commands
- Backend: `cd backend && uvicorn app.main:app --reload` · tests: `pytest`
- Frontend: `cd frontend && npm run dev` · tests: `npm test` · build: `npm run build`
- Lint: `ruff check backend/` · `npm run lint`

## Never
- Re-implement or "double-check" bridge math outside DAX.
- Invent measure/table names that aren't in the loaded metadata (stub or real).
- Commit `.env` or secrets. Fixtures contain real revenue — this repo stays internal.
- Bypass the rate limiter or the DAX guardrails, even for tests.

## Deployment
Local-only for now (company Azure deployments are paused pending networking work).
Stay 12-factor — all config via env, no hardcoded hosts — so the later Azure deploy is
a config change, not a rewrite.

## v1 is done when
The CEO can open the app → read the narrative → click the waterfall down to item level
→ ask a question in chat → pin the answer → and his layout persists. Every number
matches the Power BI report for the same period.
