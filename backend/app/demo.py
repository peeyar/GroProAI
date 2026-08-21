"""Rule-based demo narrative + chat responder. This is a placeholder for the Phase 3
LLM path: the templates only PRESENT numbers that came through the guarded query path
(fixtures in mock mode) — nothing is computed locally and there are no LLM calls."""

import re

from .metadata.models import Bucket, ModelContext
from .powerbi.mock import FixtureNotFoundError
from .powerbi.queries import bridge_query, drill_query


def _mentions(text: str, *words: str) -> bool:
    return any(re.search(rf"\b{re.escape(w)}\b", text) for w in words)


def fmt_musd(value: float) -> str:
    sign = "+" if value > 0 else "-" if value < 0 else ""
    return f"{sign}${abs(value) / 1e6:.1f}M"


def glossary_map(ctx: ModelContext) -> dict[str, str]:
    """Parse `model-context/glossary.md` bullets into {term: plain-English text}."""
    entries: dict[str, str] = {}
    current: str | None = None
    for line in ctx.glossary.splitlines():
        if m := re.match(r"^- \*\*(.+?)\*\*\s*—\s*(.*)$", line):
            current = m.group(1)
            entries[current] = m.group(2).strip()
        elif current and line.strip() and not line.startswith("#"):
            entries[current] += " " + line.strip()
        else:
            current = None
    return entries


def bridge_values(ctx: ModelContext, client, flavor: str) -> dict[str, float]:
    row = client.query_rows(bridge_query(ctx, flavor))[0]
    return {label: row[f"[{label}]"] for label, _ in ctx.bridge_measures(flavor)}


def _comparison(ctx: ModelContext, flavor: str) -> str:
    return ctx.periods.prior_year if flavor == "yoy" else ctx.periods.prior_quarter


def build_narrative(ctx: ModelContext, client, flavor: str) -> str:
    values = bridge_values(ctx, client, flavor)
    total = values.pop(ctx.total.label)
    verb = "grew" if total >= 0 else "declined"
    ranked = sorted(values.items(), key=lambda kv: abs(kv[1]), reverse=True)
    ups = [f"{label} ({fmt_musd(v)})" for label, v in ranked if v > 0]
    downs = [f"{label} ({fmt_musd(v)})" for label, v in ranked if v < 0]

    parts = [
        f"Revenue {verb} {fmt_musd(total)} in {ctx.periods.current} versus "
        f"{_comparison(ctx, flavor)} ({'year over year' if flavor == 'yoy' else 'sequentially'})."
    ]
    if ups:
        parts.append(f"The biggest tailwinds were {', '.join(ups[:3])}.")
    if downs:
        parts.append(f"Working against us: {', '.join(downs[:3])}.")
    parts.append("Click any bar to see which business units, customers, and items drove it.")
    return " ".join(parts)


def _waterfall_chart(ctx: ModelContext, client, flavor: str) -> dict:
    values = bridge_values(ctx, client, flavor)
    total = values.pop(ctx.total.label)
    return {
        "chartType": "waterfall",
        "title": f"Revenue bridge {flavor.upper()} — {ctx.periods.current} vs "
        f"{_comparison(ctx, flavor)}",
        "data": [{"name": b.label, "value": values[b.label]} for b in ctx.buckets],
        "total": total,
    }


def _level_chart(
    ctx: ModelContext, client, level: str, path: dict, value_label: str, title: str
) -> dict | None:
    target = next(d for d in ctx.drill_path if d.level == level)
    try:
        rows = client.query_rows(drill_query(ctx, "yoy", level, path))
    except FixtureNotFoundError:
        return None
    return {
        "chartType": "bar",
        "title": title,
        "data": [
            {"name": r[f"{target.table}[{target.column}]"], "value": r[f"[{value_label}]"]}
            for r in rows
        ],
    }


def _bu_rows(ctx: ModelContext, client) -> list[dict]:
    first = ctx.drill_path[0]
    try:
        rows = client.query_rows(drill_query(ctx, "yoy", first.level, {}))
    except FixtureNotFoundError:
        return []
    return [
        {"name": r[f"{first.table}[{first.column}]"], "total": r[f"[{ctx.total.label}]"]}
        for r in rows
    ]


def _bucket_reply(ctx: ModelContext, client, bucket: Bucket) -> dict:
    values = bridge_values(ctx, client, "yoy")
    gloss = glossary_map(ctx)
    first = ctx.drill_path[0]
    reply = (
        f"{bucket.label} moved revenue {fmt_musd(values[bucket.label])} year over year. "
        f"{gloss.get(bucket.label, '')} Here is how it splits by {first.label.lower()}:"
    )
    chart = _level_chart(
        ctx, client, first.level, {}, bucket.label, f"{bucket.label} (YoY) by {first.label}"
    )
    return {"reply": reply, "chart": chart}


def demo_chat_reply(ctx: ModelContext, client, message: str) -> dict:
    """Keyword-matched canned answers. Replaced in Phase 3 by NL -> DAX -> answer
    through the same guarded query path."""
    low = message.lower()
    gloss = glossary_map(ctx)
    values = bridge_values(ctx, client, "yoy")
    total = values[ctx.total.label]
    out: dict | None = None

    # A business unit mentioned by name -> its customer breakdown.
    first = ctx.drill_path[0]
    customer_level = ctx.drill_path[1] if len(ctx.drill_path) > 1 else None
    for bu in _bu_rows(ctx, client):
        if _mentions(low, bu["name"].lower()):
            reply = (
                f"{bu['name']} contributed {fmt_musd(bu['total'])} of the "
                f"{fmt_musd(total)} total YoY change. "
                f"{gloss.get(bu['name'], '')} Top customer moves:"
            )
            chart = None
            if customer_level:
                chart = _level_chart(
                    ctx, client, customer_level.level, {first.level: bu["name"]},
                    ctx.total.label, f"{bu['name']} — YoY change by {customer_level.label}",
                )
            out = {"reply": reply, "chart": chart}
            break

    if out is None and _mentions(low, "customer", "customers", "who", "account", "accounts"):
        bus = _bu_rows(ctx, client)
        if bus and customer_level:
            top = bus[0]
            out = {
                "reply": (
                    f"Across {top['name']} (the biggest mover at {fmt_musd(top['total'])}), "
                    "here are the customers behind the change:"
                ),
                "chart": _level_chart(
                    ctx, client, customer_level.level, {first.level: top["name"]},
                    ctx.total.label, f"{top['name']} — YoY change by {customer_level.label}",
                ),
            }

    if out is None and _mentions(low, "seq", "sequential", "prior quarter", "last quarter"):
        out = {
            "reply": build_narrative(ctx, client, "seq"),
            "chart": _waterfall_chart(ctx, client, "seq"),
        }

    if out is None:
        # Bucket keywords — check longer labels first so "market mix" beats "market".
        for bucket in sorted(ctx.buckets, key=lambda b: -len(b.label)):
            keywords = [bucket.label.lower()]
            if bucket.key == "fx":
                keywords += ["currency", "exchange", "euro", "dollar"]
            if bucket.key == "propulsion_mix":
                keywords += ["ev", "electric", "propulsion"]
            if _mentions(low, *keywords):
                out = _bucket_reply(ctx, client, bucket)
                break

    if out is None:
        # Default: the YoY story.
        out = {
            "reply": build_narrative(ctx, client, "yoy"),
            "chart": _waterfall_chart(ctx, client, "yoy"),
        }
        if not _mentions(low, "why", "what", "how", "change", "changed", "summary", "explain"):
            out["reply"] += (
                " (Demo mode: try asking about FX, customers, a business unit, or a bucket "
                "like Propulsion Mix.)"
            )

    out["demo"] = True
    return out
