"""Mock Power BI client (MOCK_PBI=1): serves captured fixtures keyed by the hash of
the normalized DAX text — the same cache key the live client will use."""

import hashlib
import json
from pathlib import Path


class FixtureNotFoundError(KeyError):
    pass


def normalize_dax(dax: str) -> str:
    return " ".join(dax.split())


def dax_key(dax: str) -> str:
    return hashlib.sha256(normalize_dax(dax).encode("utf-8")).hexdigest()


class MockPowerBIClient:
    def __init__(self, fixtures_dir: Path):
        self.fixtures_dir = Path(fixtures_dir)
        index_path = self.fixtures_dir / "index.json"
        if not index_path.is_file():
            raise FileNotFoundError(
                f"{index_path} missing — run `python scripts/onboard_model.py --stub` "
                "to generate it from the fixture files."
            )
        index = json.loads(index_path.read_text(encoding="utf-8"))
        self._file_by_dax: dict[str, str] = {}
        self._file_by_name: dict[str, str] = {}
        for entry in index["fixtures"]:
            self._file_by_dax[dax_key(entry["dax"])] = entry["file"]
            self._file_by_name[entry["name"]] = entry["file"]

    def _load(self, file: str) -> dict:
        return json.loads((self.fixtures_dir / file).read_text(encoding="utf-8"))

    def execute_dax(self, dax: str) -> dict:
        """Mirror the executeQueries response shape: {"results": [{"tables": [...]}]}."""
        file = self._file_by_dax.get(dax_key(dax))
        if file is None:
            raise FixtureNotFoundError(
                f"No fixture matches this query (hash {dax_key(dax)[:12]}…). "
                f"Known fixtures: {sorted(self._file_by_name)}. "
                "Capture it with scripts/onboard_model.py."
            )
        return {"results": [self._load(file)["result"]]}

    def query_rows(self, dax: str) -> list[dict]:
        return self.execute_dax(dax)["results"][0]["tables"][0]["rows"]
