import dataclasses
import json
import shutil

import pytest

from app.metadata.context import build_chat_context
from app.metadata.loader import MetadataError, load_model_context


def test_stub_model_loads(ctx):
    assert ctx.model_name == "GroPro (stub)"
    assert set(ctx.tmdl.tables) == {
        "Sales", "Business Unit", "Customer", "Product", "Region", "Period",
    }
    assert [b.key for b in ctx.buckets] == [
        "market", "market_mix", "propulsion_mix", "content", "price", "fx",
    ]
    assert [d.level for d in ctx.drill_path] == ["bu", "customer", "product", "item"]
    assert ctx.periods.current == "2026-Q2"


def test_allowlist(ctx):
    assert "Market Mix YoY" in ctx.allowlist.measures
    assert ("Product", "Item Number") in ctx.allowlist.columns
    assert "Business Unit" in ctx.allowlist.tables
    assert "Nonexistent Measure" not in ctx.allowlist.measures


def test_missing_measure_fails_at_load(settings, tmp_path):
    bad_dir = tmp_path / "stub"
    shutil.copytree(settings.model_context_dir, bad_dir)
    map_path = bad_dir / "model-map.json"
    raw = json.loads(map_path.read_text())
    raw["buckets"][0]["yoy"] = "Not A Real Measure"
    map_path.write_text(json.dumps(raw))

    bad_settings = dataclasses.replace(settings, model_context_dir=bad_dir)
    with pytest.raises(MetadataError, match="Not A Real Measure"):
        load_model_context(bad_settings)


def test_chat_context_covers_schema_and_rules(ctx):
    text = build_chat_context(ctx)
    assert "[Market Mix YoY]" in text
    assert "'Business Unit'[BU Code]" in text
    assert "DEFINE/EVALUATE" in text
    assert "Propulsion Mix" in ctx.glossary and ctx.glossary in text
