import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKEND_DIR.parent
for extra in (str(BACKEND_DIR), str(REPO_DIR / "scripts")):
    if extra not in sys.path:
        sys.path.insert(0, extra)

import pytest  # noqa: E402

from app.config import Settings  # noqa: E402
from app.metadata.loader import load_model_context  # noqa: E402
from app.powerbi.client import get_client  # noqa: E402


@pytest.fixture()
def settings(monkeypatch):
    monkeypatch.setenv("MOCK_PBI", "1")
    for var in ("MODEL_CONTEXT_DIR", "FIXTURES_DIR", "GLOSSARY_PATH"):
        monkeypatch.delenv(var, raising=False)
    return Settings.from_env()


@pytest.fixture()
def ctx(settings):
    return load_model_context(settings)


@pytest.fixture()
def client(settings):
    return get_client(settings)
