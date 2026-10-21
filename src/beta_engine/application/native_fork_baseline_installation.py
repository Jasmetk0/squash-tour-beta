"""Internal transactional staging; deliberately absent from public create routes."""

from dataclasses import dataclass

from sqlalchemy import text

from beta_engine.infrastructure.db.native_fork_installation import (
    install_native_fork_baseline_in_session,
)


@dataclass(slots=True)
class NativeForkBaselineInstallationService:
    repository: object

    def install(self, **command):
        with self.repository._session_factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            return install_native_fork_baseline_in_session(
                self.repository,
                session,
                **command,
            )
