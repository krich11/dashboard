from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    app_name: str = "Datacenter Dashboard"
    mock_mode: bool = True
    mock_scenario: str = "all_clear"
    testing: bool = False  # set TESTING=true in test runs
    database_url: str = f"sqlite:///{ROOT_DIR / 'data' / 'dashboard.db'}"
    dashboard_secret_key: str = "dev-only-change-in-production"
    dashboard_api_key: str | None = None
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    status_history_retention_days: int = 30
    status_history_max_per_device: int = 5000

    collector_interval_sec: int = 60
    collector_concurrency: int = 8
    collector_default_backoff_sec: int = 30
    collector_max_backoff_sec: int = 300
    collector_circuit_breaker_threshold: int = 5
    status_staleness_sec: int = 180

    reachability_interval_sec: int = 60
    reachability_timeout_sec: int = 5
    reachability_method: str = "ping"
    reachability_require_both_families: bool = True
    reachability_ipv4_targets: list[str] = ["1.1.1.1", "8.8.8.8"]
    reachability_ipv6_targets: list[str] = [
        "2606:4700:4700::1111",
        "2001:4860:4860::8888",
    ]
    frontend_static_dir: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()