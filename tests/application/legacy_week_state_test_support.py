from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from beta_engine.application.season_event_simulation_service import (
    SeasonEventSimulationService,
    SimulateOneEventRequest,
    SimulateOneEventResult,
)
from beta_engine.application.season_week_simulation_preflight_service import (
    SeasonWeekSimulationPreflightService,
)
from test_season_event_simulation_service import make_simulation_service


@dataclass(slots=True)
class LegacyWeekStateTestContext:
    """Build legacy diagnostic states without the retired week-run orchestrator."""

    event_simulation_service: SeasonEventSimulationService
    preflight_service: SeasonWeekSimulationPreflightService
    event_id: str
    week: int

    @property
    def lifecycle_service(self):
        return self.event_simulation_service.lifecycle_service

    @property
    def ranking_snapshot_service(self):
        return self.event_simulation_service.ranking_snapshot_service

    def simulate_event(
        self,
        *,
        seed: int = 12345,
        apply_points: bool = False,
        publish_snapshot: bool = False,
        allow_blocked: bool = False,
        allow_incomplete_results: bool = False,
    ) -> SimulateOneEventResult:
        return self.event_simulation_service.simulate_one_event(
            event_id=self.event_id,
            request=SimulateOneEventRequest(
                dry_run=False,
                seed=seed,
                apply_points=apply_points,
                publish_snapshot=publish_snapshot,
                allow_blocked=allow_blocked,
                allow_incomplete_results=allow_incomplete_results,
            ),
        )


def make_legacy_week_state_context(
    tmp_path: Path,
) -> tuple[LegacyWeekStateTestContext, str, int]:
    event_service, event_id = make_simulation_service(tmp_path)
    preflight = SeasonWeekSimulationPreflightService(
        calendar_service=event_service.lifecycle_service.calendar_service,
        lifecycle_service=event_service.lifecycle_service,
        event_simulation_service=event_service,
        ranking_snapshot_service=event_service.ranking_snapshot_service,
    )
    lifecycle = event_service.lifecycle_service.get_event_lifecycle(event_id=event_id)
    assert lifecycle.event is not None
    week = lifecycle.event.season_week
    context = LegacyWeekStateTestContext(
        event_simulation_service=event_service,
        preflight_service=preflight,
        event_id=event_id,
        week=week,
    )
    return context, event_id, week
