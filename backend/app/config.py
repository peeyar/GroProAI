"""Environment-driven settings. 12-factor: all config comes from env, nothing hardcoded."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _env_flag(env: Mapping[str, str], name: str, default: bool) -> bool:
    raw = env.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    mock_pbi: bool
    model_context_dir: Path
    fixtures_dir: Path
    glossary_path: Path
    pbi_tenant_id: str
    pbi_client_id: str
    pbi_client_secret: str
    pbi_workspace_id: str
    pbi_dataset_id: str
    anthropic_model: str

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        env = os.environ if env is None else env
        # Mock is the default: live calls must be an explicit opt-in (MOCK_PBI=0).
        mock = _env_flag(env, "MOCK_PBI", default=True)
        if mock:
            default_context = REPO_ROOT / "model-context" / "stub"
        else:
            default_context = REPO_ROOT / "model-context"
        return cls(
            mock_pbi=mock,
            model_context_dir=Path(env.get("MODEL_CONTEXT_DIR", default_context)),
            fixtures_dir=Path(env.get("FIXTURES_DIR", REPO_ROOT / "fixtures")),
            glossary_path=Path(
                env.get("GLOSSARY_PATH", REPO_ROOT / "model-context" / "glossary.md")
            ),
            pbi_tenant_id=env.get("PBI_TENANT_ID", ""),
            pbi_client_id=env.get("PBI_CLIENT_ID", ""),
            pbi_client_secret=env.get("PBI_CLIENT_SECRET", ""),
            pbi_workspace_id=env.get("PBI_WORKSPACE_ID", ""),
            pbi_dataset_id=env.get("PBI_DATASET_ID", ""),
            anthropic_model=env.get("ANTHROPIC_MODEL", ""),
        )
