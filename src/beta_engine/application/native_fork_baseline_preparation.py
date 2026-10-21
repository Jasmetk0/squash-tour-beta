"""Prepare a native fork's exact current facts without creating a Branch."""

from dataclasses import dataclass

from sqlalchemy import text

from beta_engine.infrastructure.db.native_fork_baseline import (
    prepare_native_fork_baseline_in_session,
    verify_native_fork_baseline_in_session,
)


@dataclass(slots=True)
class NativeForkBaselinePreparationService:
    repository: object

    def prepare(
        self, *, run_id, source_branch_id, source_revision_id, target_branch_id
    ):
        with self.repository._session_factory() as session:
            session.execute(text("BEGIN"))
            return prepare_native_fork_baseline_in_session(
                self.repository,
                session,
                run_id=run_id,
                source_branch_id=source_branch_id,
                source_revision_id=source_revision_id,
                target_branch_id=target_branch_id,
            )

    def verify(
        self,
        baseline,
        *,
        run_id,
        source_branch_id,
        source_revision_id,
        target_branch_id,
    ):
        with self.repository._session_factory() as session:
            session.execute(text("BEGIN"))
            return verify_native_fork_baseline_in_session(
                self.repository,
                session,
                baseline=baseline,
                run_id=run_id,
                source_branch_id=source_branch_id,
                source_revision_id=source_revision_id,
                target_branch_id=target_branch_id,
            )
