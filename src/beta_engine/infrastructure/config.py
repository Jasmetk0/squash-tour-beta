"""Config loading utilities for data-driven engine setup."""

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python <3.11 fallback for local tooling.
    import tomli as tomllib
from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    name: str = "Squash Tour Beta Engine"
    environment: str = "development"


class DatabaseConfig(BaseModel):
    url: str = "sqlite:///./beta_engine.db"


class SimulationConfig(BaseModel):
    seed: int = Field(default=42)


class Settings(BaseModel):
    app: AppConfig = AppConfig()
    database: DatabaseConfig = DatabaseConfig()
    simulation: SimulationConfig = SimulationConfig()


def load_settings(path: str | Path = "config/settings.toml") -> Settings:
    config_path = Path(path)
    if not config_path.exists():
        return Settings()
    with config_path.open("rb") as fh:
        raw_data = tomllib.load(fh)
    return Settings.model_validate(raw_data)
