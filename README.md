# GroPro AI — Revenue Bridge

A CEO-facing web app that replaces the front end of the "GroPro" Power BI monthly
revenue bridge. It answers one question — **"Revenue changed. Why?"** — with a
waterfall, drill-down to item level, a plain-English narrative, and a chat panel
that can create pinnable charts.

> **Status: working demo.** The full UI runs end to end against stub data
> (`MOCK_PBI=1`). The live Power BI connection (Phase 1) and the real AI chat
> (Phase 3) plug into the same endpoints without frontend changes.

Deeper design notes: [`docs/phase0.md`](docs/phase0.md).

## The one rule that outranks everything

**Power BI is the only calculation engine.** Every number rendered comes from a
DAX query against the published semantic model (or a captured fixture of one in
mock mode). Bridge math is never re-implemented in Python or JS — the backend
builds queries, guards them, executes them, and relays rows.

## How it works

```
Browser (React + Vite)
   │  /api/bridge · /api/drill · /api/narrative · /api/chat · /api/freshness
   ▼
FastAPI backend
   │  1. Loads model-context/ at startup (model-map.json + TMDL)
   │     → bucket bindings, drill hierarchy, DAX identifier allowlist, chat context
   │  2. Builds aggregate DAX (SUMMARIZECOLUMNS / TOPN) from that metadata
   │  3. Validates every identifier against the allowlist (guardrails)
   ▼
Power BI executeQueries API          ←  Phase 1 (live, rate-limited, cached)
   …or fixtures/ via the mock client ←  today (MOCK_PBI=1), keyed by DAX hash
```

The app is **metadata-driven**: no schema names are hardcoded. Swapping the stub
model for the real one is a config change (see *Onboarding* below), not a rewrite.

### Domain in 30 seconds

The bridge explains a revenue change between two periods — **YoY** (vs the same
quarter last year) or **SEQ** (vs the prior quarter) — as six buckets that sum to
the total: **Market** (industry volume), **Market Mix** (our customers vs the
industry), **Propulsion Mix** (gas→EV shift), **Content** ($ of parts per
vehicle), **Price**, and **FX**. Business units: **AUTO** and **HVOR**.
Plain-English definitions live in [`model-context/glossary.md`](model-context/glossary.md).

## Quickstart (demo mode)

Prereqs: Python 3.12, Node 18+.

```bash
# 1. Backend
cd backend
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
MOCK_PBI=1 .venv/bin/uvicorn app.main:app --reload          # http://127.0.0.1:8000

# 2. Frontend (separate terminal)
cd frontend
npm install
npm run dev                                                  # http://localhost:5173
```

If port 8000 is busy: run uvicorn with `--port 8010` and start the frontend with
`GROPRO_API=http://127.0.0.1:8010 npm run dev`.

**In the demo:** the app opens to the narrative + waterfall. Click a waterfall
bar to focus a bucket, drill BU → customer → product → item, toggle YoY/SEQ, ask
the chat panel questions ("Why did revenue change?", "What about HVOR?"), and
pin any chart to My View. Chat answers are canned demo rules — no LLM calls yet.

### Tests & lint

```bash
cd backend  && .venv/bin/pytest && .venv/bin/ruff check .
cd frontend && npm test && npm run lint && npm run build
```

## Repo layout

| Path | What it is |
|---|---|
| `backend/` | FastAPI (Python 3.12): metadata loader, DAX guardrails, mock Power BI client, demo API |
| `frontend/` | React + TypeScript + Vite: waterfall, drill-down, chat, My View |
| `model-context/` | `model-map.json` + TMDL + glossary — the only schema-aware config; `stub/` until the real .pbix arrives |
| `fixtures/` | Captured query results served in mock mode, indexed by DAX hash |
| `scripts/` | `onboard_model.py` (one-command model onboarding), `grain_check.py` |
| `docs/` | Deeper design notes |

## Onboarding the real model (when the .pbix arrives)

1. Export the pbix as `.pbip` in Power BI Desktop.
2. `python scripts/onboard_model.py --pbip path/to/GroPro.pbip`
   — ingests the TMDL, drafts `model-map.json` (LLM-assisted with a heuristic
   fallback; unresolved slots are `REVIEW-ME` and fail validation), pauses for
   human review, runs the grain check, and captures fixtures.
3. The **grain check** walks BU → customer → product → item with real queries.
   If item-level rows are missing from the model it STOPs and reports — the fix
   (adding a detail table to the pbix) is a modeling decision, not the app's.
4. Restart the backend; it picks up the new model.

## Configuration

All config is env-driven (12-factor). Copy `.env.example` to `.env` (gitignored):

```
PBI_TENANT_ID / PBI_CLIENT_ID / PBI_CLIENT_SECRET   # service principal
PBI_WORKSPACE_ID / PBI_DATASET_ID                   # published dataset
ANTHROPIC_API_KEY / ANTHROPIC_MODEL                 # chat + onboarding (Phase 3)
MOCK_PBI=1                                          # serve fixtures (default)
```

## Guardrails on generated DAX

- Only `DEFINE`/`EVALUATE` query syntax is accepted.
- Every identifier is validated against the allowlist built from the TMDL.
- Drill queries carry a `TOPN` cap (500 rows); always aggregate, never dump a fact table.
- The live client (Phase 1) adds rate limiting (40 q/min), 429 backoff, caching, and query logging.

## Roadmap

- [x] **Phase 0** — metadata engine on stub model, fixtures, onboarding + grain-check scripts
- [x] **Demo UI** — Official View + canned chat, end to end in mock mode
- [ ] **Phase 1** — live Power BI client (MSAL, rate limits, cache), freshness from the Service
- [ ] **Phase 2** — Official View hardening against live data
- [ ] **Phase 3** — real AI: auto-narrative + NL→DAX chat through the guarded query path
- [ ] **Phase 4** — My View server-side per-user layouts (SQLite + react-grid-layout)

## Internal use only

This repository stays private: once the real model is onboarded, `fixtures/`
contains actual revenue data. Never commit `.env` or secrets.
