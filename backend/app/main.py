"""GroPro AI backend. Phase 0 surface: health + metadata introspection.
Bridge/drill/freshness endpoints land in Phase 1."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api import router as api_router
from .config import Settings
from .metadata.loader import load_model_context
from .powerbi.client import get_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings.from_env()
    app.state.settings = settings
    app.state.model = load_model_context(settings)
    app.state.client = get_client(settings)
    yield


app = FastAPI(title="GroPro AI", lifespan=lifespan)
app.include_router(api_router)


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "mockPbi": app.state.settings.mock_pbi,
        "model": app.state.model.model_name,
    }


@app.get("/api/metadata")
async def metadata():
    ctx = app.state.model
    return {
        "model": ctx.model_name,
        "total": {"key": ctx.total.key, "label": ctx.total.label},
        "buckets": [{"key": b.key, "label": b.label} for b in ctx.buckets],
        "drillPath": [{"level": d.level, "label": d.label} for d in ctx.drill_path],
        "periods": {
            "current": ctx.periods.current,
            "priorYear": ctx.periods.prior_year,
            "priorQuarter": ctx.periods.prior_quarter,
        },
        "counts": {
            "tables": len(ctx.tmdl.tables),
            "columns": len(ctx.allowlist.columns),
            "measures": len(ctx.allowlist.measures),
        },
    }
