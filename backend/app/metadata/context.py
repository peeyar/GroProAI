"""Builds the chat system-prompt context from loaded metadata. This is the only
source of schema knowledge for NL->DAX: the LLM sees exactly the allowlisted names."""

from .models import ModelContext


def build_chat_context(ctx: ModelContext) -> str:
    lines: list[str] = [
        f"You translate a CEO's questions about the '{ctx.model_name}' revenue bridge "
        "into DAX queries against a Power BI semantic model.",
        "",
        "## Bridge measures",
        "Two flavors: YoY (vs same quarter last year) and SEQ (vs prior quarter).",
    ]
    for bucket in (*ctx.buckets, ctx.total):
        lines.append(f"- {bucket.label}: YoY = [{bucket.yoy}], SEQ = [{bucket.seq}]")

    lines += ["", "## Drill hierarchy (top to bottom)"]
    for level in ctx.drill_path:
        lines.append(f"- {level.label}: '{level.table}'[{level.column}]")

    p = ctx.periods
    lines += [
        "",
        "## Periods",
        f"Filter column: '{p.table}'[{p.column}]. "
        f"Current = \"{p.current}\", prior year = \"{p.prior_year}\", "
        f"prior quarter = \"{p.prior_quarter}\".",
        "",
        "## Tables and columns you may reference",
    ]
    for table in sorted(ctx.tmdl.tables.values(), key=lambda t: t.name):
        cols = ", ".join(f"[{c}]" for c in table.columns)
        lines.append(f"- '{table.name}': {cols}")

    lines += [
        "",
        "## Rules",
        "- Emit only DEFINE/EVALUATE query syntax.",
        "- Use only the measures, tables, and columns listed above.",
        "- Always aggregate (SUMMARIZECOLUMNS, TOPN) — never dump a fact table.",
        f"- Cap detail results with TOPN ({ctx.drill_row_cap} rows max).",
    ]

    if ctx.glossary:
        lines += ["", "## Glossary (use these plain-English explanations)", ctx.glossary]

    return "\n".join(lines)
