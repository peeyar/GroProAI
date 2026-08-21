"""Startup loader: model-map.json + TMDL -> ModelContext (allowlist, drill config,
bridge bindings, glossary). Every schema reference in the map is validated against
the TMDL so a typo fails at boot, not in a CEO-facing query."""

import json

from ..config import Settings
from .models import Allowlist, Bucket, DrillLevel, ModelContext, Periods, TmdlModel
from .tmdl import parse_tmdl_dir


class MetadataError(Exception):
    pass


def build_allowlist(tmdl: TmdlModel) -> Allowlist:
    return Allowlist(
        tables=frozenset(tmdl.tables),
        columns=tmdl.columns,
        measures=tmdl.measures,
    )


def load_model_context(settings: Settings) -> ModelContext:
    ctx_dir = settings.model_context_dir
    map_path = ctx_dir / "model-map.json"
    if not map_path.is_file():
        raise MetadataError(f"model-map.json not found at {map_path}")

    raw = json.loads(map_path.read_text(encoding="utf-8"))
    tmdl = parse_tmdl_dir(ctx_dir / "tmdl")

    total = Bucket(
        key="total",
        label=raw["total"].get("label", "Total"),
        yoy=raw["total"]["yoy"],
        seq=raw["total"]["seq"],
    )
    buckets = tuple(Bucket(b["key"], b["label"], b["yoy"], b["seq"]) for b in raw["buckets"])
    drill_path = tuple(
        DrillLevel(d["level"], d["label"], d["table"], d["column"]) for d in raw["drillPath"]
    )
    p = raw["periods"]
    periods = Periods(p["table"], p["column"], p["current"], p["priorYear"], p["priorQuarter"])

    errors: list[str] = []
    for bucket in (*buckets, total):
        for flavor in ("yoy", "seq"):
            measure = bucket.measure(flavor)
            if measure not in tmdl.measures:
                errors.append(f"measure not in TMDL: [{measure}] (bucket '{bucket.key}')")
    for level in drill_path:
        if (level.table, level.column) not in tmdl.columns:
            errors.append(
                f"drill column not in TMDL: '{level.table}'[{level.column}] "
                f"(level '{level.level}')"
            )
    if (periods.table, periods.column) not in tmdl.columns:
        errors.append(f"period column not in TMDL: '{periods.table}'[{periods.column}]")
    if errors:
        raise MetadataError(
            "model-map.json references schema that is missing from the TMDL:\n  "
            + "\n  ".join(errors)
        )

    glossary = ""
    if settings.glossary_path.is_file():
        glossary = settings.glossary_path.read_text(encoding="utf-8")

    return ModelContext(
        model_name=raw.get("modelName", "unnamed model"),
        total=total,
        buckets=buckets,
        drill_path=drill_path,
        periods=periods,
        drill_row_cap=int(raw.get("drillRowCap", 500)),
        tmdl=tmdl,
        allowlist=build_allowlist(tmdl),
        glossary=glossary,
    )
