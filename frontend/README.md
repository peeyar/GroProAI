# frontend

React + TypeScript + Vite demo UI: Official View (narrative, waterfall, drill-down,
freshness banner), demo chat panel (canned answers — real AI chat lands in Phase 3),
and a localStorage My View for pinned charts (server-side layouts land in Phase 4).

## Run the demo

```bash
# terminal 1 — backend (mock mode serves stub fixtures)
cd backend && .venv/bin/uvicorn app.main:app --reload

# terminal 2 — frontend (proxies /api to :8000)
cd frontend && npm run dev
```

Open http://localhost:5173.

- `npm run build` — typecheck + production build
- `npm test` — vitest
- `npm run lint` — typecheck
