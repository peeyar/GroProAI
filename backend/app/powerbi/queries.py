"""Builders for the standard aggregate DAX queries (bridge + drill). Every number the
app renders comes from these queries against the semantic model — bridge math is never
computed locally."""

from ..metadata.models import DrillLevel, ModelContext


def _escape(value: str) -> str:
    return value.replace('"', '""')


def _measure_lines(ctx: ModelContext, flavor: str) -> list[str]:
    return [f'"{label}", [{measure}]' for label, measure in ctx.bridge_measures(flavor)]


def bridge_query(ctx: ModelContext, flavor: str) -> str:
    measures = ",\n        ".join(_measure_lines(ctx, flavor))
    p = ctx.periods
    return (
        "EVALUATE\n"
        "CALCULATETABLE (\n"
        "    ROW (\n"
        f"        {measures}\n"
        "    ),\n"
        f"    '{p.table}'[{p.column}] = \"{_escape(p.current)}\"\n"
        ")\n"
    )


def _level(ctx: ModelContext, level: str) -> tuple[int, DrillLevel]:
    for i, d in enumerate(ctx.drill_path):
        if d.level == level:
            return i, d
    known = [d.level for d in ctx.drill_path]
    raise ValueError(f"Unknown drill level {level!r} (drill path: {known})")


def drill_query(ctx: ModelContext, flavor: str, level: str, path: dict[str, str]) -> str:
    """Values of every bridge measure at `level`, filtered by the parent `path`
    (e.g. level='product', path={'bu': 'AUTO', 'customer': 'Volkswagen'})."""
    idx, target = _level(ctx, level)
    parents = ctx.drill_path[:idx]
    missing = [d.level for d in parents if d.level not in path]
    if missing:
        raise ValueError(f"Drill to '{level}' needs parent filters for: {missing}")

    p = ctx.periods
    filters = [f"TREATAS ( {{ \"{_escape(p.current)}\" }}, '{p.table}'[{p.column}] )"]
    for parent in parents:
        value = _escape(str(path[parent.level]))
        filters.append(f"TREATAS ( {{ \"{value}\" }}, '{parent.table}'[{parent.column}] )")

    inner = ",\n        ".join(
        [f"'{target.table}'[{target.column}]", *filters, *_measure_lines(ctx, flavor)]
    )
    return (
        "EVALUATE\n"
        "TOPN (\n"
        f"    {ctx.drill_row_cap},\n"
        "    SUMMARIZECOLUMNS (\n"
        f"        {inner}\n"
        "    ),\n"
        f"    [{ctx.total.label}], DESC\n"
        ")\n"
    )


def fixture_query(ctx: ModelContext, spec: dict) -> str:
    """Rebuild the DAX for a fixture from its self-describing spec."""
    if spec["kind"] == "bridge":
        return bridge_query(ctx, spec["flavor"])
    if spec["kind"] == "drill":
        return drill_query(ctx, spec["flavor"], spec["level"], spec.get("path", {}))
    raise ValueError(f"Unknown fixture kind {spec['kind']!r} in fixture {spec.get('name')!r}")
