"""SQLAlchemy engine/session bootstrap for deterministic SQLite persistence."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker


@dataclass(frozen=True)
class DatabaseSettings:
    """Infrastructure database settings for persistence adapters."""

    url: str = "sqlite:///./beta_engine.db"
    echo: bool = False


def create_sqlite_engine(settings: DatabaseSettings) -> Engine:
    """Create SQLAlchemy engine with SQLite-safe defaults."""

    connect_args: dict[str, object] = {}
    if settings.url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine = create_engine(settings.url, future=True, echo=settings.echo, connect_args=connect_args)

    if settings.url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragmas(dbapi_connection: object, _connection_record: object) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a reusable SQLAlchemy session factory."""

    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)
