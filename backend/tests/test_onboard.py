import json

from onboard_model import REVIEW_ME, heuristic_model_map

from app.powerbi.queries import fixture_query


def test_heuristic_draft_maps_the_stub_model(ctx):
    draft = heuristic_model_map(ctx.tmdl)

    assert draft["total"]["yoy"] == "Total Revenue Change YoY"
    assert draft["total"]["seq"] == "Total Revenue Change SEQ"

    by_key = {b["key"]: b for b in draft["buckets"]}
    assert by_key["market"]["yoy"] == "Market YoY"
    assert by_key["market_mix"]["yoy"] == "Market Mix YoY"
    assert by_key["propulsion_mix"]["seq"] == "Propulsion Mix SEQ"
    assert by_key["fx"]["seq"] == "FX SEQ"
    assert REVIEW_ME not in {b[f] for b in draft["buckets"] for f in ("yoy", "seq")}

    levels = {d["level"]: d for d in draft["drillPath"]}
    assert levels["bu"]["table"] == "Business Unit"
    assert levels["customer"] == {
        "level": "customer", "label": "Customer", "table": "Customer", "column": "Customer Name",
    }
    assert levels["item"]["column"] == "Item Number"
    assert draft["periods"]["table"] == "Period"
    assert draft["periods"]["column"] == "Quarter"
    # Data values (which quarter is current) are always a human decision.
    assert draft["periods"]["current"] == REVIEW_ME


def test_fixture_index_matches_query_builders(ctx, settings):
    index = json.loads((settings.fixtures_dir / "index.json").read_text())
    assert index["fixtures"]
    for entry in index["fixtures"]:
        spec = json.loads((settings.fixtures_dir / entry["file"]).read_text())
        assert fixture_query(ctx, spec) == entry["dax"], entry["name"]
