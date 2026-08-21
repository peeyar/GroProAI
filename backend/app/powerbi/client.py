from ..config import Settings
from .mock import MockPowerBIClient


def get_client(settings: Settings):
    if settings.mock_pbi:
        return MockPowerBIClient(settings.fixtures_dir)
    raise NotImplementedError(
        "Live Power BI client (MSAL auth, rate limiting, cache) lands in Phase 1. "
        "Run with MOCK_PBI=1 until then."
    )
