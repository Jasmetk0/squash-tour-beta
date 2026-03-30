"""Backward-compatible database bootstrap wrapper."""

from beta_engine.infrastructure.db import (
    DatabaseSettings,
    SimulationPersistenceRepository,
    create_session_factory,
    create_sqlite_engine,
)


class Database:
    """Database facade exposing SQLAlchemy engine and persistence repository."""

    def __init__(self, settings: DatabaseSettings) -> None:
        self._settings = settings
        self.engine = create_sqlite_engine(settings)
        self.session_factory = create_session_factory(self.engine)
        self.persistence = SimulationPersistenceRepository(engine=self.engine, session_factory=self.session_factory)

    @property
    def url(self) -> str:
        return self._settings.url

    def bootstrap_schema(self) -> None:
        self.persistence.bootstrap_schema()


def create_database(settings: DatabaseSettings | None = None) -> Database:
    return Database(settings or DatabaseSettings())
