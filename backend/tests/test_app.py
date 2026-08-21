from fastapi.testclient import TestClient

from app.main import app


def test_health_and_metadata(monkeypatch):
    monkeypatch.setenv("MOCK_PBI", "1")
    for var in ("MODEL_CONTEXT_DIR", "FIXTURES_DIR", "GLOSSARY_PATH"):
        monkeypatch.delenv(var, raising=False)

    with TestClient(app) as tc:
        health = tc.get("/api/health").json()
        assert health["status"] == "ok"
        assert health["mockPbi"] is True

        meta = tc.get("/api/metadata").json()
        assert len(meta["buckets"]) == 6
        assert meta["drillPath"][-1]["level"] == "item"
        assert meta["counts"]["measures"] >= 14
