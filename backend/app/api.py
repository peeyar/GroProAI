"""Demo API surface: bridge, drill, narrative, chat, freshness.
Phase 1 swaps the mock client for the live rate-limited Power BI client and
Phase 3 swaps the canned chat for the real LLM path — the response shapes stay."""

import json

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from .demo import build_narrative, demo_chat_reply, glossary_map
from .powerbi.mock import FixtureNotFoundError
from .powerbi.queries import bridge_query, drill_query

router = APIRouter(prefix="/api")

_FLAVORS = ("yoy", "seq")


def _check_flavor(flavor: str) -> None:
    if flavor not in _FLAVORS:
        raise HTTPException(status_code=422, detail=f"flavor must be one of {_FLAVORS}")


@router.get("/bridge")
async def bridge(request: Request, flavor: str = "yoy"):
    _check_flavor(flavor)
    ctx = request.app.state.model
    try:
        row = request.app.state.client.query_rows(bridge_query(ctx, flavor))[0]
    except FixtureNotFoundError as exc:
        raise HTTPException(
            status_code=503, detail=f"Bridge data for '{flavor}' isn't captured yet."
        ) from exc
    gloss = glossary_map(ctx)
    comparison = ctx.periods.prior_year if flavor == "yoy" else ctx.periods.prior_quarter
    return {
        "flavor": flavor,
        "period": {"current": ctx.periods.current, "comparison": comparison},
        "buckets": [
            {
                "key": b.key,
                "label": b.label,
                "value": row[f"[{b.label}]"],
                "description": gloss.get(b.label, ""),
            }
            for b in ctx.buckets
        ],
        "total": {
            "key": "total",
            "label": ctx.total.label,
            "value": row[f"[{ctx.total.label}]"],
            "description": gloss.get("Revenue bridge", ""),
        },
    }


@router.get("/drill")
async def drill(request: Request, level: str, flavor: str = "yoy", path: str = "{}"):
    _check_flavor(flavor)
    ctx = request.app.state.model
    try:
        path_filters = json.loads(path)
        if not isinstance(path_filters, dict):
            raise ValueError("path must be a JSON object")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Bad path filter: {exc}") from exc

    try:
        dax = drill_query(ctx, flavor, level, path_filters)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    idx = next(i for i, d in enumerate(ctx.drill_path) if d.level == level)
    target = ctx.drill_path[idx]
    next_level = ctx.drill_path[idx + 1].level if idx + 1 < len(ctx.drill_path) else None

    try:
        rows = request.app.state.client.query_rows(dax)
    except FixtureNotFoundError:
        return {
            "level": level,
            "label": target.label,
            "nextLevel": next_level,
            "rows": [],
            "note": (
                "That slice isn't in the demo capture yet — in demo mode, follow the top "
                "row at each level. Live queries land in Phase 1."
            ),
        }

    return {
        "level": level,
        "label": target.label,
        "nextLevel": next_level,
        "rows": [
            {
                "name": r[f"{target.table}[{target.column}]"],
                "values": {b.key: r[f"[{b.label}]"] for b in ctx.buckets},
                "total": r[f"[{ctx.total.label}]"],
            }
            for r in rows
        ],
        "note": None,
    }


@router.get("/narrative")
async def narrative(request: Request, flavor: str = "yoy"):
    _check_flavor(flavor)
    ctx = request.app.state.model
    return {
        "flavor": flavor,
        "text": build_narrative(ctx, request.app.state.client, flavor),
        "demo": True,
    }


class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
async def chat(request: Request, body: ChatRequest):
    ctx = request.app.state.model
    return demo_chat_reply(ctx, request.app.state.client, body.message)


@router.get("/freshness")
async def freshness(request: Request):
    ctx = request.app.state.model
    return {
        "period": ctx.periods.current,
        "mode": "demo",
        "message": (
            f"Demo data — stub fixtures for {ctx.periods.current}. "
            "Live Power BI refresh lands in Phase 1."
        ),
    }
