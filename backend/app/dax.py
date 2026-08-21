"""Guardrails for every DAX query the app sends — hand-built or LLM-generated.
Phase 0 covers the shape check and identifier allowlist; Phase 3 layers on
TOPN injection and query logging."""

import re

from .metadata.models import Allowlist


class DaxValidationError(Exception):
    pass


# 'Quoted Table'[X] | Table[X] | [X]  — bare [X] is a measure or query-local alias.
_REF_RE = re.compile(
    r"(?:'(?P<qtable>[^']+)'|(?P<utable>[A-Za-z_][A-Za-z0-9_]*))?\[(?P<name>[^\]]+)\]"
)
# "Alias", <expr> — column aliases defined inside ROW/SUMMARIZECOLUMNS/ADDCOLUMNS.
_ALIAS_RE = re.compile(r'"([^"]+)"\s*,')


def validate_dax(dax: str, allowlist: Allowlist) -> list[str]:
    """Return a list of violations (empty = valid)."""
    stripped = dax.strip()
    if not stripped:
        return ["Empty query."]
    head = stripped.split(None, 1)[0].upper()
    if head not in ("DEFINE", "EVALUATE"):
        return ["Only DEFINE/EVALUATE query syntax is accepted."]

    aliases = {m.group(1) for m in _ALIAS_RE.finditer(dax)}
    errors: list[str] = []
    for m in _REF_RE.finditer(dax):
        table = m.group("qtable") or m.group("utable")
        name = m.group("name").strip()
        if table:
            if (table, name) not in allowlist.columns:
                errors.append(f"Unknown column: '{table}'[{name}]")
        elif name not in allowlist.measures and name not in aliases:
            errors.append(f"Unknown measure: [{name}]")
    return list(dict.fromkeys(errors))


def assert_valid_dax(dax: str, allowlist: Allowlist) -> None:
    errors = validate_dax(dax, allowlist)
    if errors:
        raise DaxValidationError("DAX rejected by guardrails:\n  " + "\n  ".join(errors))
