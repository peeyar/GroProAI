import pytest

from app.dax import DaxValidationError, assert_valid_dax, validate_dax
from app.powerbi.queries import bridge_query, drill_query


def test_bridge_queries_pass_guardrails(ctx):
    for flavor in ("yoy", "seq"):
        dax = bridge_query(ctx, flavor)
        assert dax.startswith("EVALUATE")
        assert validate_dax(dax, ctx.allowlist) == []


def test_drill_query_is_capped_and_valid(ctx):
    dax = drill_query(ctx, "yoy", "customer", {"bu": "AUTO"})
    assert "TOPN (" in dax
    assert str(ctx.drill_row_cap) in dax
    assert validate_dax(dax, ctx.allowlist) == []


def test_drill_requires_parent_filters(ctx):
    with pytest.raises(ValueError, match="parent"):
        drill_query(ctx, "yoy", "item", {"bu": "AUTO"})


def test_unknown_drill_level_rejected(ctx):
    with pytest.raises(ValueError, match="Unknown drill level"):
        drill_query(ctx, "yoy", "warehouse", {})


def test_rejects_non_evaluate_syntax(ctx):
    errors = validate_dax("SELECT * FROM Sales", ctx.allowlist)
    assert errors and "DEFINE/EVALUATE" in errors[0]


def test_rejects_unknown_identifiers(ctx):
    with pytest.raises(DaxValidationError, match="Unknown measure"):
        assert_valid_dax('EVALUATE ROW ( "x", [Made Up Measure] )', ctx.allowlist)
    with pytest.raises(DaxValidationError, match="Unknown column"):
        assert_valid_dax("EVALUATE VALUES ( 'Customer'[Shoe Size] )", ctx.allowlist)
