import pytest

from app.config import Settings
from app.powerbi.client import get_client
from app.powerbi.mock import FixtureNotFoundError
from app.powerbi.queries import bridge_query, drill_query


def test_bridge_fixture_served_by_dax_hash(ctx, client):
    rows = client.query_rows(bridge_query(ctx, "yoy"))
    assert len(rows) == 1
    assert rows[0]["[Total]"] == pytest.approx(42_300_000.0)

    rows = client.query_rows(bridge_query(ctx, "seq"))
    assert rows[0]["[Total]"] == pytest.approx(-8_400_000.0)


def test_drill_chain_to_item_level(ctx, client):
    rows = client.query_rows(drill_query(ctx, "yoy", "bu", {}))
    assert [r["Business Unit[BU Code]"] for r in rows] == ["AUTO", "HVOR"]

    rows = client.query_rows(drill_query(ctx, "yoy", "customer", {"bu": "AUTO"}))
    assert rows[0]["Customer[Customer Name]"] == "Volkswagen"

    rows = client.query_rows(
        drill_query(
            ctx, "yoy", "item",
            {"bu": "AUTO", "customer": "Volkswagen", "product": "Battery Housings"},
        )
    )
    assert len(rows) == 6
    assert rows[0]["Product[Item Number]"] == "BH-1001"


def test_unknown_query_raises_fixture_error(client):
    with pytest.raises(FixtureNotFoundError, match="No fixture matches"):
        client.query_rows('EVALUATE ROW ( "x", 1 )')


def test_live_client_is_not_available_yet(monkeypatch):
    monkeypatch.setenv("MOCK_PBI", "0")
    with pytest.raises(NotImplementedError, match="Phase 1"):
        get_client(Settings.from_env())
