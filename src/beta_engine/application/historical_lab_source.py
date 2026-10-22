"""Read one authenticated Saved boundary, never live runtime or Package state.

The selected Branch is a reachability context; components retain their actual
pre-fork owner. Native source dependencies are resolved in the same SQLite read
snapshot as the lineage proof. Returned copies have no live database link.
"""

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict
from sqlalchemy import text

from beta_engine.application.native_fork_runtime_reducer import source_inputs
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.calendar.season_weeks import age_at_calendar_position
from beta_engine.domain.matches.health import project_player_health
from beta_engine.domain.players.calendar_canonical_match import canonical_participant
from beta_engine.domain.players.calendar_health import CalendarHealthProfile
from beta_engine.domain.players.health import PlayerHealthProfile
from beta_engine.domain.players.sporting import PlayerSportingRecord
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.simulation_slots import (
    CanonicalMatchInputProjectionPolicy,
    project_player,
)
from beta_engine.infrastructure.db.models import RunBranchModel, RunContainerModel
from beta_engine.infrastructure.db.native_fork_runtime_state import (
    native_read_proof_scope,
)
from beta_engine.infrastructure.db.player_sporting_state import (
    load_saved_sporting_bundle,
)


class HistoricalLabPlayer(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal["historical_lab_player.v1"] = "historical_lab_player.v1"
    run_id: str
    selected_branch_id: str
    owner_branch_id: str
    saved_revision_id: str
    saved_revision_content_hash: str
    week: RunWeekPosition
    sporting_fingerprint: str
    profile_fingerprint: str
    biography: dict
    player: PlayerSportingRecord
    # Keep the versioned health dates, including a genuinely older source week.
    health: CalendarHealthProfile | PlayerHealthProfile | None
    health_source_week: dict | None
    health_fingerprint: str | None
    scope: str = "Complete stored sporting record and biography; MatchEngine consumes the canonical seven-value projection. Health numeric effects/healing are not invented."

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode="json"))


@dataclass
class HistoricalLabSource:
    revision: object
    selected_branch_id: str
    inputs: object
    sporting: object
    week: RunWeekPosition

    def player(self, player_id: str) -> HistoricalLabPlayer:
        record = next(
            (p for p in self.sporting.players if p.player_id == player_id), None
        )
        if record is None:
            raise ValueError(
                "Player has no sporting record at the selected Saved boundary (not yet born or unsupported state)"
            )
        world = self.inputs.world
        original = (
            next((p for p in world.players if p.player_id == player_id), None)
            if world
            else None
        )
        life = self.inputs.lifecycle
        identity = (
            next((p for p in life.players if p.player_id == player_id), None)
            if life
            else None
        )
        if original is not None:
            bio = {
                "player_id": player_id,
                "name": original.name,
                "nationality": original.nationality,
                "birth_year": original.birth_year,
                "birth_year_week": original.birth_year_week,
                "play_style": original.play_style,
                "archetype": original.archetype,
                "hidden_career_traits": original.hidden_career_traits.model_dump(
                    mode="json"
                )
                if original.hidden_career_traits
                else None,
            }
            fingerprint = original.source_generation_fingerprint
        else:
            source = self.inputs.prospects
            if source is not None:
                source = source.for_week(self.week.ordinal)
            prospect = (
                next((p for p in source.records if p["prospect_id"] == player_id), None)
                if source
                else None
            )
            if identity is None or prospect is None or not prospect.get("display_name"):
                raise ValueError(
                    "Saved born player lacks authenticated lifecycle/biography provenance"
                )
            bio = {
                "player_id": player_id,
                "name": prospect["display_name"],
                "nationality": prospect["country_code"],
                "birth_year": identity.birth_year,
                "birth_year_week": identity.birth_year_week,
                "play_style": "unspecified",
                "archetype": "unspecified",
                "hidden_career_traits": None,
            }
            fingerprint = getattr(
                identity, "source_generation_fingerprint", None
            ) or canonical_hash(prospect)
        position = self.week.calendar_position
        bio["age"] = age_at_calendar_position(
            birth_year=bio["birth_year"],
            birth_year_week=bio["birth_year_week"],
            calendar_year=position.calendar_year,
            year_week=position.year_week,
            weeks_per_calendar_year=self.week.calendar.weeks_per_year,
        )
        bio["status"] = getattr(identity, "status", "active")
        health_state = self.inputs.health
        health = (
            next((p for p in health_state.players if p.player_id == player_id), None)
            if health_state
            else None
        )
        if health_state is not None and health is None:
            raise ValueError("Saved player is missing from its Health authority")
        return HistoricalLabPlayer(
            run_id=self.revision.run_id,
            selected_branch_id=self.selected_branch_id,
            owner_branch_id=self.revision.branch_id,
            saved_revision_id=self.revision.revision_id,
            saved_revision_content_hash=self.revision.content_hash,
            week=self.week,
            sporting_fingerprint=self.sporting.fingerprint,
            profile_fingerprint=fingerprint,
            biography=bio,
            player=record,
            health=health,
            health_source_week=(
                getattr(
                    health_state, "source_health_week", health_state.week
                ).model_dump(mode="json")
                if health_state
                else None
            ),
            health_fingerprint=health_state.fingerprint if health_state else None,
        )


def match_projection(snapshot: HistoricalLabPlayer):
    if snapshot.biography["status"] == "retired":
        raise ValueError("Retired player cannot play a Lab match")
    if (
        snapshot.health is not None
        and project_player_health(snapshot.health).numeric_calibration_required
    ):
        raise ValueError(
            "Historical Health requires unsupported numeric effects; no healthy substitution is allowed"
        )
    bio = snapshot.biography
    projection = project_player(
        snapshot.player,
        source_sporting_fingerprint=snapshot.sporting_fingerprint,
        policy=CanonicalMatchInputProjectionPolicy(),
        profile_source_fingerprint=snapshot.profile_fingerprint,
        profile_provenance="Authenticated selected Saved boundary; complete source retained in Lab evidence",
        **{
            key: bio[key]
            for key in (
                "age",
                "name",
                "nationality",
                "play_style",
                "archetype",
                "hidden_career_traits",
            )
        },
    )
    return projection, canonical_participant(projection)


@contextmanager
def historical_lab_source(repository, *, run_id, branch_id, revision_id):
    with repository._session_factory() as session, native_read_proof_scope():
        session.execute(text("BEGIN"))
        branch = session.get(RunBranchModel, branch_id)
        if (
            session.get(RunContainerModel, run_id) is None
            or branch is None
            or branch.run_id != run_id
        ):
            raise KeyError("Historical Lab source Run/Branch was not found")
        lineage = repository._validated_branch_revision_lineage_in_session(
            session=session,
            branch=branch,
            payload_revision_ids=frozenset({revision_id}),
        )
        revision = next((r for r in lineage if r.revision_id == revision_id), None)
        if revision is None:
            raise KeyError(
                "Saved Revision is not reachable from the selected Run/Branch"
            )
        inputs = source_inputs(revision, repository, session)
        sporting = inputs.checkpoint
        if sporting is None:
            bundle = load_saved_sporting_bundle(
                revision.payload, run_id=run_id, branch_id=revision.branch_id
            )
            sporting = bundle[0][-1] if bundle and bundle[0] else None
        if sporting is None:
            raise ValueError(
                "Saved Revision has no supported complete sporting state; seven-value Initial World alone is insufficient"
            )
        metadata = revision.payload["run"]
        calendar = (
            RunCalendar.from_metadata(metadata["run_calendar"])
            if "run_calendar" in metadata
            else RunCalendar.legacy_fax()
        )
        # Use the selected Saved envelope, including its historical horizon.
        week = RunWeekPosition(
            calendar=calendar,
            season_index=sporting.week.season_index,
            week=sporting.week.week,
        )
        yield HistoricalLabSource(revision, branch_id, inputs, sporting, week)
