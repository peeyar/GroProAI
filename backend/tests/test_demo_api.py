import json

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def tc(monkeypatch):
    monkeypatch.setenv("MOCK_PBI", "1")
    for var in ("MODEL_CONTEXT_DIR", "FIXTURES_DIR", "GLOSSARY_PATH"):
        monkeypatch.delenv(var, raising=False)
    with TestClient(app) as client:
        yield client


def test_bridge_endpoint(tc):
    body = tc.get("/api/bridge", params={"flavor": "yoy"}).json()
    assert body["total"]["value"] == pytest.approx(42_300_000.0)
    assert [b["key"] for b in body["buckets"]][:2] == ["market", "market_mix"]
    assert body["buckets"][0]["description"]  # glossary tooltip text
    assert body["period"] == {"current": "2026-Q2", "comparison": "2025-Q2"}

    seq = tc.get("/api/bridge", params={"flavor": "seq"}).json()
    assert seq["total"]["value"] == pytest.approx(-8_400_000.0)


def test_bridge_rejects_bad_flavor(tc):
    assert tc.get("/api/bridge", params={"flavor": "mom"}).status_code == 422


def test_drill_endpoint_walks_the_chain(tc):
    bu = tc.get("/api/drill", params={"level": "bu"}).json()
    assert [r["name"] for r in bu["rows"]] == ["AUTO", "HVOR"]
    assert bu["nextLevel"] == "customer"

    hvor = tc.get(
        "/api/drill", params={"level": "customer", "path": json.dumps({"bu": "HVOR"})}
    ).json()
    assert hvor["rows"][0]["name"] == "Daimler Truck"

    item = tc.get(
        "/api/drill",
        params={
            "level": "item",
            "path": json.dumps(
                {"bu": "AUTO", "customer": "Volkswagen", "product": "Battery Housings"}
            ),
        },
    ).json()
    assert len(item["rows"]) == 6
    assert item["nextLevel"] is None


def test_drill_uncaptured_slice_is_graceful(tc):
    body = tc.get(
        "/api/drill", params={"level": "customer", "path": json.dumps({"bu": "MARINE"})}
    ).json()
    assert body["rows"] == []
    assert "demo" in body["note"].lower()


def test_drill_missing_parent_is_422(tc):
    assert tc.get("/api/drill", params={"level": "item"}).status_code == 422


def test_narrative_reads_fixture_numbers(tc):
    body = tc.get("/api/narrative", params={"flavor": "yoy"}).json()
    assert "+$42.3M" in body["text"]
    assert body["demo"] is True


def test_chat_fx_question(tc):
    body = tc.post("/api/chat", json={"message": "How did FX move this year?"}).json()
    assert body["demo"] is True
    assert "+$6.0M" in body["reply"]
    assert body["chart"]["chartType"] == "bar"


def test_chat_bu_question(tc):
    body = tc.post("/api/chat", json={"message": "What happened in HVOR?"}).json()
    assert "+$15.5M" in body["reply"]
    assert body["chart"]["data"][0]["name"] == "Daimler Truck"


def test_chat_default_returns_waterfall(tc):
    body = tc.post("/api/chat", json={"message": "Why did revenue change?"}).json()
    assert body["chart"]["chartType"] == "waterfall"
    assert len(body["chart"]["data"]) == 6


def test_freshness(tc):
    body = tc.get("/api/freshness").json()
    assert body["mode"] == "demo"
    assert "2026-Q2" in body["message"]
