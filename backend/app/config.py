from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    app_name: str = "Datacenter Dashboard"
    mock_mode: bool = True
    mock_scenario: str = "all_clear"
    database_url: str = f"sqlite:///{ROOT_DIR / 'data' / 'dashboard.db'}"
    dashboard_secret_key: str = ""
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()