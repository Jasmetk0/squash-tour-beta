"""Machine-readable pre-alpha FAX release-test input profile.

This service does not simulate or mutate a Run. It verifies the decided Master v72
minimum shape required before the long 50-season acceptance command is meaningful.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from beta_engine.application.calendar_package_run_adapter import CalendarPackageRunAdapter
from beta_engine.infrastructure.db.initial_world_state import get_initial_world
from beta_engine.infrastructure.db.models import RunBranchModel, RunContainerModel
from beta_engine.infrastructure.db.run_package_state import get_run_package_state


FAX_ACCEPTANCE_START_SEASON = 2000
FAX_ACCEPTANCE_END_SEASON = 2049
FAX_ACCEPTANCE_SEASON_COUNT = 50
FAX_ACCEPTANCE_FIRST_SEASON = "2000/2001"
FAX_ACCEPTANCE_MIN_INITIAL_PLAYERS = 1000
FAX_ACCEPTANCE_WORLD_TOUR_EDITIONS = 80


class PreAlphaFaxAcceptanceIssue(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    severity: Literal["error", "info"]
    code: str = Field(min_length=1, max_length=96)
    message: str = Field(min_length=1, max_length=500)


class PreAlphaFaxAcceptanceProfile(BaseModel):
    """Read-only release-gate input evidence for one editable Run/Branch."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["pre_alpha_fax_acceptance_profile.v1"] = (
        "pre_alpha_fax_acceptance_profile.v1"
    )
    run_id: str
    branch_id: str
    ready_for_long_acceptance: bool
    editable_run: bool
    active_branch: bool

    timeline_start_season: int
    timeline_end_season: int
    timeline_season_count: int
    required_timeline_start_season: int = FAX_ACCEPTANCE_START_SEASON
    required_timeline_end_season: int = FAX_ACCEPTANCE_END_SEASON
    required_timeline_season_count: int = FAX_ACCEPTANCE_SEASON_COUNT

    initial_world_ready: bool
    initial_world_fingerprint: str | None = None
    initial_player_count: int = 0
    required_min_initial_players: int = FAX_ACCEPTANCE_MIN_INITIAL_PLAYERS
    initial_world_package_id: str | None = None

    calendar_ready: bool
    calendar_package_id: str
    calendar_state_fingerprint: str | None = None
    calendar_fingerprint: str | None = None
    calendar_event_count: int = 0
    world_tour_edition_count: int = 0
    required_world_tour_edition_count: int = FAX_ACCEPTANCE_WORLD_TOUR_EDITIONS
    lower_tour_edition_count: int = 0

    issues: tuple[PreAlphaFaxAcceptanceIssue, ...]

    @property
    def fingerprint(self) -> str:
        payload = self.model_dump(mode="json", exclude={"profile_fingerprint"})
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    @computed_field
    @property
    def profile_fingerprint(self) -> str:
        return self.fingerprint


class PreAlphaFaxAcceptanceProfileService:
    """Inspect only canonical Run-owned state; never use live source registries."""

    def __init__(self, session_factory):
        self._session_factory = session_factory

    def inspect(self, *, run_id: str, branch_id: str) -> PreAlphaFaxAcceptanceProfile:
        issues: list[PreAlphaFaxAcceptanceIssue] = []
        package_id = CalendarPackageRunAdapter.package_id_for_season(
            FAX_ACCEPTANCE_FIRST_SEASON
        )

        with self._session_factory() as session:
            run = session.get(RunContainerModel, run_id)
            branch = session.get(RunBranchModel, branch_id)
            if run is None:
                raise KeyError(f"Run {run_id!r} was not found")
            if branch is None or branch.run_id != run_id:
                raise KeyError(
                    f"Branch {branch_id!r} was not found in Run {run_id!r}"
                )

            editable_run = not bool(run.read_only)
            active_branch = branch.status == "active"
            if not editable_run:
                issues.append(
                    PreAlphaFaxAcceptanceIssue(
                        severity="error",
                        code="FAX_ACCEPTANCE_RUN_READ_ONLY",
                        message="The release-test copy must be an editable Run.",
                    )
                )
            if not active_branch:
                issues.append(
                    PreAlphaFaxAcceptanceIssue(
                        severity="error",
                        code="FAX_ACCEPTANCE_BRANCH_INACTIVE",
                        message="The release-test Branch must be active.",
                    )
                )

            timeline_start = int(run.timeline_start_season)
            timeline_end = int(run.timeline_end_season)
            timeline_count = timeline_end - timeline_start + 1
            if (
                timeline_start != FAX_ACCEPTANCE_START_SEASON
                or timeline_end != FAX_ACCEPTANCE_END_SEASON
                or timeline_count != FAX_ACCEPTANCE_SEASON_COUNT
            ):
                issues.append(
                    PreAlphaFaxAcceptanceIssue(
                        severity="error",
                        code="FAX_ACCEPTANCE_TIMELINE_INVALID",
                        message=(
                            "The release-test Run must cover the canonical 50-season "
                            "timeline 2000/01–2049/50."
                        ),
                    )
                )

            world = get_initial_world(
                session, run_id=run_id, branch_id=branch_id
            )
            initial_count = len(world.players) if world is not None else 0
            if world is None:
                issues.append(
                    PreAlphaFaxAcceptanceIssue(
                        severity="error",
                        code="FAX_ACCEPTANCE_INITIAL_WORLD_MISSING",
                        message="Adopt and save a Run-owned Initial World before the long acceptance.",
                    )
                )
            elif initial_count < FAX_ACCEPTANCE_MIN_INITIAL_PLAYERS:
                issues.append(
                    PreAlphaFaxAcceptanceIssue(
                        severity="error",
                        code="FAX_ACCEPTANCE_INITIAL_PLAYER_COUNT_LOW",
                        message=(
                            f"Initial World has {initial_count} active players; "
                            f"Master v72 requires at least {FAX_ACCEPTANCE_MIN_INITIAL_PLAYERS}."
                        ),
                    )
                )

            package_state = get_run_package_state(
                session, run_id=run_id, branch_id=branch_id
            )
            calendar = None
            if package_state is None:
                issues.append(
                    PreAlphaFaxAcceptanceIssue(
                        severity="error",
                        code="FAX_ACCEPTANCE_CALENDAR_PACKAGE_MISSING",
                        message=(
                            f"Run has no applied {package_id} Calendar Package."
                        ),
                    )
                )
            else:
                try:
                    calendar = CalendarPackageRunAdapter.project_calendar(
                        package_state, package_id=package_id
                    )
                except ValueError as exc:
                    issues.append(
                        PreAlphaFaxAcceptanceIssue(
                            severity="error",
                            code="FAX_ACCEPTANCE_CALENDAR_PACKAGE_INVALID",
                            message=str(exc),
                        )
                    )

            events = tuple(calendar.calendar.events) if calendar is not None else ()
            world_tour = tuple(
                event for event in events if event.tour_level == "WORLD_TOUR"
            )
            lower_tour = tuple(
                event for event in events if event.tour_level != "WORLD_TOUR"
            )
            if calendar is not None and len(world_tour) != FAX_ACCEPTANCE_WORLD_TOUR_EDITIONS:
                issues.append(
                    PreAlphaFaxAcceptanceIssue(
                        severity="error",
                        code="FAX_ACCEPTANCE_WORLD_TOUR_EDITION_COUNT",
                        message=(
                            f"First-season Calendar has {len(world_tour)} World Tour Editions; "
                            f"the reference release-test template requires "
                            f"{FAX_ACCEPTANCE_WORLD_TOUR_EDITIONS}."
                        ),
                    )
                )

            if calendar is not None:
                issues.append(
                    PreAlphaFaxAcceptanceIssue(
                        severity="info",
                        code="FAX_ACCEPTANCE_LOWER_TOURS_ABSTRACT",
                        message=(
                            f"{len(lower_tour)} non-World-Tour Editions are present; "
                            "Master v72 permits lower Tours to remain abstract in this release test."
                        ),
                    )
                )

            errors = tuple(issue for issue in issues if issue.severity == "error")
            return PreAlphaFaxAcceptanceProfile(
                run_id=run_id,
                branch_id=branch_id,
                ready_for_long_acceptance=not errors,
                editable_run=editable_run,
                active_branch=active_branch,
                timeline_start_season=timeline_start,
                timeline_end_season=timeline_end,
                timeline_season_count=timeline_count,
                initial_world_ready=world is not None,
                initial_world_fingerprint=(world.fingerprint if world is not None else None),
                initial_player_count=initial_count,
                initial_world_package_id=(world.world_package_id if world is not None else None),
                calendar_ready=calendar is not None,
                calendar_package_id=package_id,
                calendar_state_fingerprint=(
                    calendar.run_package_state_fingerprint
                    if calendar is not None
                    else None
                ),
                calendar_fingerprint=(
                    calendar.content_fingerprint if calendar is not None else None
                ),
                calendar_event_count=len(events),
                world_tour_edition_count=len(world_tour),
                lower_tour_edition_count=len(lower_tour),
                issues=tuple(issues),
            )
