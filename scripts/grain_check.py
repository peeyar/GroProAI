#!/usr/bin/env python3
"""Grain check: verify the semantic model can serve item-level rows by walking the
drill hierarchy (bu -> customer -> product -> item) with real queries.

Runs at onboarding. If item-level rows are missing, STOP and report — the fix
(adding a detail table to the pbix) is Raj's call, not the app's.
"""

import argparse
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_DIR / "backend"))

from app.config import Settings  # noqa: E402
from app.metadata.loader import load_model_context  # noqa: E402
from app.metadata.models import ModelContext  # noqa: E402
from app.powerbi.client import get_client  # noqa: E402
from app.powerbi.mock import FixtureNotFoundError  # noqa: E402
from app.powerbi.queries import drill_query  # noqa: E402


def run_grain_check(ctx: ModelContext, client, flavor: str = "yoy") -> tuple[bool, str]:
    deepest = ctx.drill_path[-1]
    if (deepest.table, deepest.column) not in ctx.allowlist.columns:
        return False, (
            f"STOP: the model has no '{deepest.table}'[{deepest.column}] column, so "
            f"'{deepest.level}'-level drill is impossible."
        )

    path: dict[str, str] = {}
    rows: list[dict] = []
    for level in ctx.drill_path:
        dax = drill_query(ctx, flavor, level.level, path)
        try:
            rows = client.query_rows(dax)
        except FixtureNotFoundError as exc:
            return False, f"STOP: no captured data for drill level '{level.level}': {exc}"
        if not rows:
            return False, (
                f"STOP: zero rows at drill level '{level.level}' "
                f"('{level.table}'[{level.column}]) with filters {path or '(none)'}."
            )
        if level is not deepest:
            path[level.level] = rows[0][f"{level.table}[{level.column}]"]

    return True, (
        f"PASS: {len(rows)} rows at the deepest level '{deepest.level}' "
        f"('{deepest.table}'[{deepest.column}]) via sample path {path}."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--flavor", default="yoy", choices=["yoy", "seq"])
    args = parser.parse_args(argv)

    settings = Settings.from_env()
    ctx = load_model_context(settings)
    try:
        client = get_client(settings)
    except NotImplementedError as exc:
        print(f"Cannot query the model: {exc}")
        return 3

    ok, msg = run_grain_check(ctx, client, args.flavor)
    print(msg)
    if not ok:
        print(
            "\nItem-level rows are missing from the model. STOP — the fix (adding a "
            "detail table to the pbix) is Raj's call."
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
