"""SQLite-ready database connection bootstrap."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DatabaseSettings:
    url: str = "sqlite:///./beta_engine.db"


class Database:
    """Minimal database holder for future engine persistence wiring."""

    def __init__(self, settings: DatabaseSettings) -> None:
        self._settings = settings

    @property
    def url(self) -> str:
        return self._settings.url


def create_database(settings: DatabaseSettings | None = None) -> Database:
    return Database(settings or DatabaseSettings())
