"""Minimal TMDL reader: extracts table, column, and measure NAMES only.
Expressions stay in Power BI — the app never interprets DAX definitions."""

import re
from pathlib import Path

from .models import TmdlModel, TmdlTable


class TmdlParseError(Exception):
    pass


_TABLE_RE = re.compile(r"^table\s+(.+?)\s*$")
_COLUMN_RE = re.compile(r"^\s+column\s+(.+?)\s*$")
_MEASURE_RE = re.compile(r"^\s+measure\s+(.+?)\s*=")


def _unquote(name: str) -> str:
    name = name.strip()
    if len(name) >= 2 and name[0] == name[-1] and name[0] in ("'", '"'):
        return name[1:-1]
    return name


def parse_tmdl_dir(path: Path) -> TmdlModel:
    """Parse every .tmdl file under `path` (recursively — .pbip exports nest tables/)."""
    if not path.is_dir():
        raise TmdlParseError(f"TMDL directory not found: {path}")

    tables: dict[str, dict[str, list[str]]] = {}
    current: dict[str, list[str]] | None = None

    for file in sorted(path.rglob("*.tmdl")):
        current = None
        for line in file.read_text(encoding="utf-8").splitlines():
            if m := _TABLE_RE.match(line):
                name = _unquote(m.group(1))
                current = tables.setdefault(name, {"columns": [], "measures": []})
            elif current is not None:
                if m := _MEASURE_RE.match(line):
                    current["measures"].append(_unquote(m.group(1)))
                elif m := _COLUMN_RE.match(line):
                    current["columns"].append(_unquote(m.group(1)))

    if not tables:
        raise TmdlParseError(f"No tables found in any .tmdl file under {path}")

    return TmdlModel(
        tables={
            name: TmdlTable(name, tuple(parts["columns"]), tuple(parts["measures"]))
            for name, parts in tables.items()
        }
    )
