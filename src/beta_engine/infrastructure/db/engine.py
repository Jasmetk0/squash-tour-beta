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
    # Saved storage for Runs CREATED through this engine. None reads the
    # BETA_ENGINE_NEW_RUN_SAVED_STORAGE environment variable; unset/"v1" keeps
    # the original inline v1 storage. "saved_v2" is an explicit opt-in. Existing
    # Runs always keep the format recorded (or not recorded) at their creation.
    new_run_saved_storage: str | None = None


def create_sqlite_engine(settings: DatabaseSettings) -> Engine:
    """Create SQLAlchemy engine with SQLite-safe defaults."""

    connect_args: dict[str, object] = {}
    if settings.url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        # Browser preflights and Saves share one writer with sporting commands.
        # Allow bounded queueing while their reviewed transactions finish.
        connect_args["timeout"] = 30.0

    engine = create_engine(settings.url, future=True, echo=settings.echo, connect_args=connect_args)

    if settings.url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragmas(dbapi_connection: object, _connection_record: object) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

    from beta_engine.infrastructure.db.saved_v2_hooks import configure_new_run_storage

    configure_new_run_storage(engine, settings.new_run_saved_storage)
    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a reusable SQLAlchemy session factory."""

    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)
