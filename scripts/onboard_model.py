#!/usr/bin/env python3
"""Onboard a Power BI semantic model into GroPro AI.

Real flow (once the .pbix exists — Raj exports it as .pbip in Power BI Desktop):

    python scripts/onboard_model.py --pbip path/to/GroPro.pbip

    1. Ingest the TMDL from the .pbip export into model-context/tmdl/.
    2. Draft model-context/model-map.json (LLM via ANTHROPIC_MODEL; heuristic
       fallback when --no-llm or MOCK_PBI=1).
    3. Pause so Raj can review and edit the draft.
    4. Validate the map against the TMDL and run the grain check
       (item-level rows missing -> STOP, exit 2).
    5. Capture the standard fixtures into fixtures/ (live mode only).

Stub flow (Phase 0):

    python scripts/onboard_model.py --stub

    Regenerates fixtures/index.json by pairing each fixture file's self-describing
    spec with the DAX the query builders produce for it.
"""

import argparse
import json
import re
import shutil
import sys
from dataclasses import replace
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_DIR / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from grain_check import run_grain_check  # noqa: E402

from app.config import Settings  # noqa: E402
from app.dax import assert_valid_dax  # noqa: E402
from app.metadata.loader import MetadataError, load_model_context  # noqa: E402
from app.metadata.models import ModelContext, TmdlModel, TmdlTable  # noqa: E402
from app.metadata.tmdl import parse_tmdl_dir  # noqa: E402
from app.powerbi.client import get_client  # noqa: E402
from app.powerbi.queries import fixture_query  # noqa: E402

REVIEW_ME = "REVIEW-ME"

# Assignment order matters: specific buckets claim their measures before "market"
# sweeps up what's left. Output is re-sorted into canonical bridge order.
_BUCKET_KEYWORDS = [
    ("market_mix", "Market Mix", ["market mix", "mkt mix", "customer mix"]),
    ("propulsion_mix", "Propulsion Mix", ["propulsion", "powertrain"]),
    ("content", "Content", ["content", "cpv"]),
    ("price", "Price", ["price", "pricing"]),
    ("fx", "FX", ["fx", "currency", "exchange"]),
    ("market", "Market", ["market"]),
]
_CANONICAL_ORDER = ["market", "market_mix", "propulsion_mix", "content", "price", "fx"]

_LEVEL_KEYWORDS = [
    ("bu", "Business Unit", ["business unit", "segment", "division", "bu"]),
    ("customer", "Customer", ["customer", "oem"]),
    ("product", "Product Line", ["product line", "product"]),
    ("item", "Item", ["item", "part", "material"]),
]
_KEYISH = ("key", "id", "guid")


def _word_match(keyword: str, text: str) -> bool:
    return re.search(rf"\b{re.escape(keyword)}\b", text.lower()) is not None


def _flavor_of(name: str) -> str | None:
    low = name.lower()
    if "yoy" in low or "y/y" in low or "vs py" in low:
        return "yoy"
    if "seq" in low or "qoq" in low or "q/q" in low or "vs pq" in low:
        return "seq"
    return None


def _is_keyish(column: str) -> bool:
    return any(_word_match(k, column) for k in _KEYISH)


def _pick_column(table: TmdlTable, keywords: list[str]) -> str | None:
    candidates = [c for c in table.columns if not _is_keyish(c)]
    for kw in keywords:
        for col in candidates:
            if _word_match(kw, col):
                return col
    for hint in ("name", "code", "number"):
        for col in candidates:
            if _word_match(hint, col):
                return col
    return candidates[0] if candidates else None


def _find_level(tmdl: TmdlModel, keywords: list[str]) -> tuple[str, str] | None:
    for kw in keywords:
        for table in tmdl.tables.values():
            if _word_match(kw, table.name):
                col = _pick_column(table, keywords)
                if col:
                    return table.name, col
    for kw in keywords:
        for table in tmdl.tables.values():
            for col in table.columns:
                if _word_match(kw, col) and not _is_keyish(col):
                    return table.name, col
    return None


def _find_periods(tmdl: TmdlModel) -> tuple[str, str] | None:
    for kw in ("period", "calendar", "date", "time"):
        for table in tmdl.tables.values():
            if _word_match(kw, table.name):
                for col in table.columns:
                    if "quarter" in col.lower():
                        return table.name, col
    return None


def heuristic_model_map(tmdl: TmdlModel, model_name: str = "GroPro (draft)") -> dict:
    """Keyword-based draft of model-map.json. Every unresolved slot is REVIEW-ME,
    which fails validation at finalize — so nothing unreviewed can slip through."""
    notes: list[str] = []
    unused = set(tmdl.measures)

    total: dict[str, str] = {"label": "Total"}
    for flavor in ("yoy", "seq"):
        found = next(
            (m for m in sorted(unused) if _word_match("total", m) and _flavor_of(m) == flavor),
            None,
        )
        if found:
            unused.discard(found)
        else:
            notes.append(f"total.{flavor}: no measure matched")
        total[flavor] = found or REVIEW_ME

    by_key: dict[str, dict] = {}
    for key, label, keywords in _BUCKET_KEYWORDS:
        entry = {"key": key, "label": label}
        for flavor in ("yoy", "seq"):
            found = None
            for kw in keywords:
                found = next(
                    (m for m in sorted(unused) if _word_match(kw, m) and _flavor_of(m) == flavor),
                    None,
                )
                if found:
                    break
            if found:
                unused.discard(found)
            else:
                notes.append(f"buckets.{key}.{flavor}: no measure matched")
            entry[flavor] = found or REVIEW_ME
        by_key[key] = entry
    buckets = [by_key[k] for k in _CANONICAL_ORDER]

    drill_path = []
    for level, label, keywords in _LEVEL_KEYWORDS:
        hit = _find_level(tmdl, keywords)
        if not hit:
            notes.append(f"drillPath.{level}: no table/column matched")
        drill_path.append(
            {
                "level": level,
                "label": label,
                "table": hit[0] if hit else REVIEW_ME,
                "column": hit[1] if hit else REVIEW_ME,
            }
        )

    period_hit = _find_periods(tmdl)
    if not period_hit:
        notes.append("periods: no period table/quarter column matched")
    periods = {
        "table": period_hit[0] if period_hit else REVIEW_ME,
        "column": period_hit[1] if period_hit else REVIEW_ME,
        "current": REVIEW_ME,
        "priorYear": REVIEW_ME,
        "priorQuarter": REVIEW_ME,
    }

    return {
        "modelName": model_name,
        "total": total,
        "buckets": buckets,
        "drillPath": drill_path,
        "periods": periods,
        "drillRowCap": 500,
        "_review": notes or ["all slots matched — still verify every name against the report"],
    }


def llm_model_map(tmdl_dir: Path, draft: dict) -> dict:
    """Ask the LLM to refine the heuristic draft using the full TMDL text."""
    import os

    model = os.environ.get("ANTHROPIC_MODEL")
    if not model:
        raise RuntimeError("ANTHROPIC_MODEL env var is required for LLM drafting")
    import anthropic

    tmdl_text = "\n\n".join(
        f.read_text(encoding="utf-8") for f in sorted(tmdl_dir.rglob("*.tmdl"))
    )
    prompt = (
        "Here is the TMDL of a Power BI semantic model for a monthly revenue bridge "
        "(six buckets: Market, Market Mix, Propulsion Mix, Content, Price, FX; flavors "
        "YoY and SEQ; drill path business unit -> customer -> product -> item).\n\n"
        f"```tmdl\n{tmdl_text}\n```\n\n"
        "Correct and complete this draft model-map.json. Use ONLY measure/table/column "
        "names that appear in the TMDL. Keep the exact same JSON shape. Where you are "
        f'unsure, leave "{REVIEW_ME}". Reply with the JSON object only.\n\n'
        f"{json.dumps(draft, indent=2)}"
    )
    response = anthropic.Anthropic().messages.create(
        model=model, max_tokens=4000, messages=[{"role": "user", "content": prompt}]
    )
    text = response.content[0].text
    return json.loads(text[text.index("{") : text.rindex("}") + 1])


def find_tmdl_dir(pbip_path: Path) -> Path:
    """Locate the TMDL definition folder inside a .pbip export."""
    root = pbip_path if pbip_path.is_dir() else pbip_path.parent
    for candidate in sorted(root.glob("*.SemanticModel/definition")):
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(
        f"No *.SemanticModel/definition folder found near {pbip_path} — "
        "export the pbix as .pbip (File > Save As) in Power BI Desktop first."
    )


def ingest_tmdl(src: Path, context_dir: Path) -> Path:
    dest = context_dir / "tmdl"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    copied = 0
    for file in sorted(src.rglob("*.tmdl")):
        target = dest / file.relative_to(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, target)
        copied += 1
    if not copied:
        raise FileNotFoundError(f"No .tmdl files found under {src}")
    print(f"Ingested {copied} TMDL files into {dest}")
    return dest


def regenerate_index(ctx: ModelContext, fixtures_dir: Path) -> None:
    entries = []
    for file in sorted(fixtures_dir.glob("*.json")):
        if file.name == "index.json":
            continue
        spec = json.loads(file.read_text(encoding="utf-8"))
        dax = fixture_query(ctx, spec)
        assert_valid_dax(dax, ctx.allowlist)
        entries.append({"name": spec["name"], "file": file.name, "dax": dax})
    payload = {"generatedBy": "scripts/onboard_model.py", "fixtures": entries}
    (fixtures_dir / "index.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(f"Wrote {fixtures_dir / 'index.json'} ({len(entries)} fixtures)")


def capture_fixtures(ctx: ModelContext, client, fixtures_dir: Path) -> None:
    """Capture the standard fixture set live: both bridges, then the drill chain
    following the top row at each level."""
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    entries = []

    def run(spec: dict) -> list[dict]:
        dax = fixture_query(ctx, spec)
        assert_valid_dax(dax, ctx.allowlist)
        rows = client.query_rows(dax)
        file = f"{spec['name']}.json"
        payload = {**spec, "source": "captured", "result": {"tables": [{"rows": rows}]}}
        (fixtures_dir / file).write_text(json.dumps(payload, indent=2) + "\n")
        entries.append({"name": spec["name"], "file": file, "dax": dax})
        print(f"Captured {file} ({len(rows)} rows)")
        return rows

    for flavor in ("yoy", "seq"):
        run({"name": f"bridge_{flavor}", "kind": "bridge", "flavor": flavor, "path": {}})

    path: dict[str, str] = {}
    for level in ctx.drill_path:
        rows = run(
            {
                "name": f"drill_{level.level}_yoy",
                "kind": "drill",
                "flavor": "yoy",
                "level": level.level,
                "path": dict(path),
            }
        )
        if not rows:
            raise RuntimeError(f"Capture got zero rows at level '{level.level}' — aborting.")
        path[level.level] = rows[0][f"{level.table}[{level.column}]"]

    payload = {"generatedBy": "scripts/onboard_model.py", "fixtures": entries}
    (fixtures_dir / "index.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(f"Wrote {fixtures_dir / 'index.json'} ({len(entries)} fixtures)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--stub", action="store_true", help="regenerate fixtures/index.json")
    source.add_argument("--pbip", type=Path, help="path to the .pbip export (file or folder)")
    source.add_argument("--tmdl", type=Path, help="path to a TMDL definition folder")
    parser.add_argument("--context-dir", type=Path, default=REPO_DIR / "model-context")
    parser.add_argument("--fixtures-dir", type=Path, default=REPO_DIR / "fixtures")
    parser.add_argument("--no-llm", action="store_true", help="heuristic draft only")
    parser.add_argument("--yes", action="store_true", help="skip the review pause")
    args = parser.parse_args(argv)

    settings = Settings.from_env()

    if args.stub:
        ctx = load_model_context(settings)
        regenerate_index(ctx, args.fixtures_dir)
        return 0

    src = find_tmdl_dir(args.pbip) if args.pbip else args.tmdl
    tmdl_dir = ingest_tmdl(src, args.context_dir)
    tmdl = parse_tmdl_dir(tmdl_dir)

    draft = heuristic_model_map(tmdl, model_name=src.parent.name or "GroPro")
    if not args.no_llm and not settings.mock_pbi:
        try:
            draft = llm_model_map(tmdl_dir, draft)
        except Exception as exc:  # noqa: BLE001 — heuristic fallback is always safe
            print(f"LLM drafting failed ({exc}); keeping the heuristic draft.")

    map_path = args.context_dir / "model-map.json"
    if map_path.exists():
        backup = map_path.with_suffix(".json.bak")
        shutil.copy2(map_path, backup)
        print(f"Backed up existing map to {backup}")
    map_path.write_text(json.dumps(draft, indent=2) + "\n")
    print(f"Draft written to {map_path}")

    if not args.yes:
        input("Review/edit model-map.json now, then press Enter to validate and continue... ")

    settings = replace(settings, model_context_dir=args.context_dir)
    try:
        ctx = load_model_context(settings)
    except MetadataError as exc:
        print(f"\nmodel-map.json failed validation:\n{exc}")
        print("Fix the map (or the REVIEW-ME slots) and rerun.")
        return 1

    try:
        client = get_client(settings)
    except NotImplementedError as exc:
        print(f"Cannot query the model yet: {exc}")
        return 3

    ok, msg = run_grain_check(ctx, client)
    print(msg)
    if not ok:
        print(
            "\nItem-level rows are missing from the model. STOP — the fix (adding a "
            "detail table to the pbix) is Raj's call."
        )
        return 2

    if settings.mock_pbi:
        print("MOCK_PBI=1 — skipping live capture; regenerating the index instead.")
        regenerate_index(ctx, args.fixtures_dir)
    else:
        capture_fixtures(ctx, client, args.fixtures_dir)

    print("Onboarding complete. Restart the backend to pick up the new model.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
