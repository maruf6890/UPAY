"""Central settings. Every value can be overridden through environment variables or .env"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    # paths
    data_dir: Path = ROOT / "data_store"
    artifact_dir: Path = ROOT / "artifacts"

    # PostgreSQL (source of truth for data, alert reviews, audit log, model runs)
    database_url: str = "postgresql://upay:upay@localhost:5434/upay_pulse"
    auto_migrate: bool = False       # True = API applies pending migrations on startup (dev convenience)

    # LLM (Gemini through LangChain)
    google_api_key: str | None = None
    gemini_model: str = "gemini-flash-latest"
    llm_temperature: float | None = None  # None = model default (recommended for Gemini 3.x)

    # synthetic data
    n_agents: int = 300
    start_date: str = "2025-05-01"
    end_date: str = "2026-06-30"
    seed: int = 42

    # modelling
    test_days: int = 60
    val_days: int = 30
    train_sample_frac: float = 0.5
    n_estimators: int = 400
    reserve_bdt: float = 5000.0          # minimum cash / float an agent wants left over
    commission_rate: float = 0.005       # ASSUMPTION: 0.5% revenue on transaction value (for BDT impact)
    demo_as_of: str = "2026-05-20 08:00"  # 8 days before Eid-ul-Adha 2026 (good risk mix)


    @property
    def dsn(self) -> str:
        """asyncpg wants a plain postgresql:// DSN (tolerates a +driver suffix copied from other tools)."""
        import re
        return re.sub(r"^(postgres(?:ql)?)\+\w+://", r"postgresql://", self.database_url)


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.data_dir.mkdir(parents=True, exist_ok=True)
    s.artifact_dir.mkdir(parents=True, exist_ok=True)
    return s
