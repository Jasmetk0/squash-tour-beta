"""Calendar preflight for new Run-owned player generation, including previews."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from beta_engine.infrastructure.db import SimulationPersistenceRepository


@dataclass(frozen=True, slots=True)
class RunWorldGenerationCalendarGuard:
    """Verify the saved Run clock before doing legacy 2000/FAX generation.

    This preflight is read-only. Adoption retains its own transactional gate;
    archived proposal reads do not regenerate and never call this guard.
    """

    repository: SimulationPersistenceRepository

    def __call__(self, run_id: str, branch_id: str) -> None:
        # Keep persistence imports local: the repository imports generation
        # consumers during database package initialization.
        from beta_engine.application.run_calendar_read_authority import (
            guard_versioned_sporting_write,
        )

        with self.repository._session_factory() as session:
            guard_versioned_sporting_write(
                session, run_id=run_id, branch_id=branch_id,
                operation="Initial player generation",
            )
