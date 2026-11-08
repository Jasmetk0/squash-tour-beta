"""Read-only bridge from copied Run Calendar and persisted canonical Draw."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from beta_engine.application.calendar_package_run_adapter import (
    CalendarPackageRunAdapter,
)
from beta_engine.domain.tournaments.fax_reference_player_draw import (
    FaxReferencePlayerDraw,
)
from beta_engine.infrastructure.db.run_package_state import get_run_package_state
from beta_engine.infrastructure.db.tournament_draw_authority import (
    TournamentDrawAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_draw_input_authority import (
    TournamentDrawInputAuthorityStore,
)


@dataclass(slots=True)
class FaxReferencePlayerDrawService:
    factory: sessionmaker[Session]

    def inspect(
        self,
        *,
        run_id: str,
        branch_id: str,
        season: str,
        event_id: str,
    ) -> FaxReferencePlayerDraw:
        """Read the Run-owned copy, never a mutable Global Calendar or template."""
        with self.factory() as session:
            state = get_run_package_state(session, run_id=run_id, branch_id=branch_id)
            if state is None:
                raise ValueError("FAX player Draw requires copied Run Package state")
            calendar = CalendarPackageRunAdapter.project_calendar(
                state,
                package_id=CalendarPackageRunAdapter.package_id_for_season(season),
            )
            event = next(
                (e for e in calendar.calendar.events if e.event_id == event_id), None
            )
            if event is None:
                raise KeyError(
                    f"FAX Edition '{event_id}' is absent from copied Run Calendar"
                )
            source_entity = next(
                e
                for e in state.entities
                if e.source_package_id == calendar.package_id
                and e.source_entity_id == event_id
            )
            if (
                source_entity.content_fingerprint
                != source_entity.source_baseline_fingerprint
            ):
                raise ValueError(
                    "FAX reference Draw cannot authenticate an edited Calendar Edition"
                )
            draw_input = TournamentDrawInputAuthorityStore(session).get(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
            )
            draw = TournamentDrawAuthorityStore(session).get_initial(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
            )
            if draw_input is None or draw is None:
                raise ValueError(
                    "FAX player Draw requires committed initial Draw Input and Draw"
                )
            return FaxReferencePlayerDraw(
                run_package_state_fingerprint=state.fingerprint,
                calendar_projection_fingerprint=calendar.fingerprint,
                source_event=event,
                draw_input=draw_input,
                draw=draw,
            )
