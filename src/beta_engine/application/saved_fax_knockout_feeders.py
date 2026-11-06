"""Authenticate one explicit Saved head before deriving its initial FAX feeders."""

from __future__ import annotations

from dataclasses import dataclass

from beta_engine.application.calendar_package_run_adapter import (
    CalendarPackageRunAdapter,
)
from beta_engine.application.canonical_knockout_feeders import (
    CanonicalKnockoutFeederPlan,
    freeze_knockout_feeder_plan,
)
from beta_engine.application.run_calendar_read_authority import (
    resolve_revision_run_calendar,
)
from beta_engine.domain.tournaments.draw_authority import TournamentDrawAuthority
from beta_engine.domain.tournaments.draw_input_authority import (
    TournamentDrawInputAuthority,
)
from beta_engine.domain.tournaments.fax_reference_player_draw import (
    FaxReferencePlayerDraw,
)
from beta_engine.infrastructure.db.repositories import SimulationPersistenceRepository
from beta_engine.infrastructure.db.run_package_state import load_saved_run_package_state
from beta_engine.infrastructure.db.simulation_slot_state import (
    load_saved_simulation_slot_component,
)


@dataclass(slots=True)
class SavedFaxKnockoutFeederService:
    repository: SimulationPersistenceRepository

    def prepare(
        self,
        *,
        run_id: str,
        branch_id: str,
        season: str,
        event_id: str,
        expected_saved_revision_id: str,
    ) -> CanonicalKnockoutFeederPlan:
        state = self.repository.get_branch_revision_state(branch_id=branch_id)
        revision = state.saved_revision
        if (state.run_id, state.saved_head_revision_id, revision.branch_id) != (
            run_id,
            expected_saved_revision_id,
            branch_id,
        ):
            raise ValueError(
                "FAX feeder source changed or requires a materialized Branch-owned Saved root"
            )
        return self._from_revision(
            revision=revision,
            run_id=run_id,
            branch_id=branch_id,
            season=season,
            event_id=event_id,
        )

    def reload(self, plan: CanonicalKnockoutFeederPlan) -> CanonicalKnockoutFeederPlan:
        """Reauthenticate the original reachable Saved source after later Saves.

        Never resolve a serialized plan by ID alone or silently adopt the latest
        head. Native inherited-Branch remapping still needs its own v4 consumer.
        """
        run_id, branch_id = plan.source.draw.run_id, plan.source.draw.branch_id
        history = self.repository.get_branch_saved_revision_history(
            run_id=run_id,
            branch_id=branch_id,
        )
        revision = next(
            (
                r
                for r in history.saved_revisions
                if r.revision_id == plan.source_saved_revision_id
            ),
            None,
        )
        if revision is None or revision.branch_id != branch_id:
            raise ValueError(
                "Feeder source revision is not reachable in its exact owner Branch"
            )
        rebuilt = self._from_revision(
            revision=revision,
            run_id=run_id,
            branch_id=branch_id,
            season=str(plan.source.source_event.season),
            event_id=plan.source.draw.event_id,
        )
        if rebuilt != plan:
            raise ValueError(
                "Serialized feeder plan differs from authenticated Saved source"
            )
        return rebuilt

    def _from_revision(self, *, revision, run_id, branch_id, season, event_id):
        packages = load_saved_run_package_state(
            revision.payload, run_id=run_id, branch_id=branch_id
        )
        if packages is None:
            raise ValueError("Save the copied FAX Calendar before preparing feeders")
        calendar = CalendarPackageRunAdapter.project_calendar(
            packages,
            package_id=CalendarPackageRunAdapter.package_id_for_season(season),
        )
        event = next(
            (e for e in calendar.calendar.events if e.event_id == event_id), None
        )
        if event is None:
            raise KeyError("FAX feeder Edition is absent from this Saved Calendar")
        entity = next(
            e
            for e in packages.entities
            if e.source_package_id == calendar.package_id
            and e.source_entity_id == event_id
        )
        if entity.content_fingerprint != entity.source_baseline_fingerprint:
            raise ValueError(
                "FAX feeder source Edition was edited after Package adoption"
            )
        component = (
            load_saved_simulation_slot_component(
                revision.payload, run_id=run_id, branch_id=branch_id
            )
            or {}
        )
        if any(r["event_id"] == event_id for r in component.get("draw_revisions", ())):
            raise ValueError(
                "Revised Draw needs its versioned native execution boundary"
            )
        inputs = next(
            (r for r in component.get("draw_inputs", ()) if r["event_id"] == event_id),
            None,
        )
        draw = next(
            (
                r
                for r in component.get("draw_authorities", ())
                if r["event_id"] == event_id
            ),
            None,
        )
        if inputs is None or draw is None:
            raise ValueError("Manual Save of canonical Draw Input and Draw is required")
        source = FaxReferencePlayerDraw(
            run_package_state_fingerprint=packages.fingerprint,
            calendar_projection_fingerprint=calendar.fingerprint,
            source_event=event,
            draw_input=TournamentDrawInputAuthority.model_validate_json(
                inputs["payload_json"]
            ),
            draw=TournamentDrawAuthority.model_validate_json(draw["payload_json"]),
        )
        with self.repository._session_factory() as session:
            clock = resolve_revision_run_calendar(
                session,
                run_id=run_id,
                revision_id=revision.revision_id,
                _repository=self.repository,
            )
        return freeze_knockout_feeder_plan(
            source=source,
            source_saved_revision_id=revision.revision_id,
            source_saved_content_hash=revision.content_hash,
            calendar=clock,
        )
