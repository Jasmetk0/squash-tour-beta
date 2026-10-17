"""One real Run-calendar-native standalone MatchEngine command with manual Save.

This is deliberately *not* a 61-week SimulationSlot, tournament result, point
award, or weekly transition. First vertical slice: a saved v2 population, two
current players, opening week, one actual rally-by-rally exhibition.
"""
from __future__ import annotations

from dataclasses import dataclass

from pydantic import Field
from sqlalchemy import select, text

from beta_engine.application.run_calendar_read_authority import resolve_saved_run_calendar
from beta_engine.core import DeterministicRng
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.matches.match_engine import MatchEngine
from beta_engine.domain.matches.models import MatchContext, MatchParticipantContext
from beta_engine.domain.players.models import Player
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.infrastructure.db.calendar_standalone_match_state import (
    CalendarStandaloneMatch, load_match_rows, load_saved_calendar_match, put_match,
)
from beta_engine.infrastructure.db.initial_world_state import (
    get_initial_world, load_saved_initial_world,
)
from beta_engine.infrastructure.db.models import (
    RunContainerModel, RunBranchModel, SimulationSlotModel,
    PlayerSportingWeekStateModel, PlayerHealthWeekStateModel,
    AuthoritativeWorldStateModel,
)


class CalendarStandaloneMatchCommand(FrozenInput):
    command_id: str = Field(min_length=1, max_length=128)
    match_id: str = Field(min_length=1, max_length=128)
    expected_saved_head: str = Field(min_length=1, max_length=128)
    expected_initial_world_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    player_a_id: str = Field(min_length=1, max_length=128)
    player_b_id: str = Field(min_length=1, max_length=128)
    seed: int
    operator_label: str = Field(min_length=1, max_length=160)
    audit_reason: str = Field(min_length=1, max_length=1000)


@dataclass(slots=True)
class CalendarStandaloneMatchService:
    repository: object

    @staticmethod
    def _engine_player(profile) -> Player:
        # v2 initial population is currently seven-value, rather than a
        # sporting 57-attribute week state. The conversion is an explicit
        # compatibility projection, not claims of completed development.
        a = profile.attributes
        return Player(
            player_id=profile.player_id,
            name=profile.name,
            age=profile.age_years_at_season_start,
            nationality=profile.nationality,
            technique=max(1, min(99, a.technique)),
            movement=max(1, min(99, a.movement)),
            physical=max(1, min(99, a.physical)),
            mental=max(1, min(99, a.mental)),
            consistency=max(1, min(99, a.consistency)),
            clutch=max(1, min(99, a.clutch)),
            recovery=max(1, min(99, a.recovery)),
            play_style=profile.play_style,
            archetype=profile.archetype,
            hidden_career_traits=profile.hidden_career_traits,
        )

    def _context(self, session, *, run_id: str, branch_id: str):
        run = session.get(RunContainerModel, run_id)
        branch = session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise KeyError("Calendar match Run/Branch not found")
        if (
            run.read_only or run.storage_kind != "custom_local"
            or run.status != "working" or branch.read_only
            or branch.status != "active"
        ):
            raise ValueError("Calendar match requires an active writable custom Run/Branch")
        clock = resolve_saved_run_calendar(session, run_id=run_id, branch_id=branch_id)
        if clock.schema_version != "run_calendar.v1":
            raise ValueError("Calendar match requires versioned Run calendar")
        state = self.repository._validated_branch_revision_state_in_session(
            session=session, branch=branch,
        )
        if state.working_draft.status != "clean":
            raise ValueError("Save or discard pending Working Draft before calendar match")
        world = get_initial_world(session, run_id=run_id, branch_id=branch_id)
        saved = load_saved_initial_world(
            state.saved_revision.payload, run_id=run_id, branch_id=branch_id
        )
        if (
            world is None or saved is None
            or world.schema_version != "initial_world_state.v2"
            or saved.fingerprint != world.fingerprint
        ):
            raise ValueError("Calendar match requires a fully Saved v2 initial population")
        origin = world.run_calendar
        if (
            (clock.weeks_per_year, clock.season_start_year_week, clock.start_year)
            != (origin.weeks_per_year, origin.season_start_year_week, origin.start_year)
            or clock.season_count < origin.season_count
        ):
            raise ValueError("Calendar match source clock differs from Saved population")
        # Do not pretend that non-neutral injuries, sporting effects or a
        # different temporal owner can be consumed before their W migration.
        for model in (
            SimulationSlotModel, PlayerSportingWeekStateModel,
            PlayerHealthWeekStateModel, AuthoritativeWorldStateModel,
        ):
            if session.scalar(select(model.run_id).where(
                model.run_id == run_id, model.branch_id == branch_id
            ).limit(1)) is not None:
                raise ValueError("Calendar match cannot bypass existing sporting/Health state")
        return clock, state, world

    def inspect(self, *, run_id: str, branch_id: str) -> dict:
        with self.repository._session_factory() as session:
            session.execute(text("BEGIN"))
            clock, revision, world = self._context(session, run_id=run_id, branch_id=branch_id)
            rows = load_match_rows(session, run_id=run_id, branch_id=branch_id)
            saved = load_saved_calendar_match(
                revision.saved_revision.payload, run_id=run_id, branch_id=branch_id
            )
            if saved is not None and (not rows or rows[0].fingerprint != saved.fingerprint):
                raise ValueError("Saved calendar match differs from live match")
            if len(rows) > 1:
                raise ValueError("Standalone calendar match v1 allows one completed match")
            return {
                "schema_version": "calendar_standalone_match_inspection.v1",
                "run_id": run_id,
                "branch_id": branch_id,
                "run_calendar": clock.to_metadata(),
                "saved_head_revision_id": revision.saved_head_revision_id,
                "draft_version": revision.working_draft.draft_version,
                "initial_world_fingerprint": world.fingerprint,
                "player_ids": [p.player_id for p in world.players],
                "match": rows[0].model_dump(mode="json") if rows else None,
                "match_fingerprint": rows[0].fingerprint if rows else None,
                "saved": saved is not None,
            }

    def simulate(self, *, run_id: str, branch_id: str, command: CalendarStandaloneMatchCommand) -> dict:
        request_fp = canonical_hash({
            "run_id": run_id, "branch_id": branch_id,
            "command": command.model_dump(mode="json"),
        })
        with self.repository._session_factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            clock, revision, world = self._context(session, run_id=run_id, branch_id=branch_id)
            existing = load_match_rows(session, run_id=run_id, branch_id=branch_id)
            if existing:
                match = existing[0]
                if (
                    len(existing) != 1 or match.command_id != command.command_id
                    or match.request_fingerprint != request_fp
                ):
                    raise ValueError("Standalone match already played; conflicting command")
                return {"match": match.model_dump(mode="json"), "fingerprint": match.fingerprint}
            if revision.saved_head_revision_id != command.expected_saved_head:
                raise ValueError("Calendar match Saved HEAD changed since review")
            if world.fingerprint != command.expected_initial_world_fingerprint:
                raise ValueError("Calendar match population changed since review")
            if command.player_a_id == command.player_b_id:
                raise ValueError("Calendar match requires two distinct players")
            players = {p.player_id: p for p in world.players}
            if command.player_a_id not in players or command.player_b_id not in players:
                raise ValueError("Both calendar match players must belong to Saved population")
            match_context = MatchContext(
                match_id=command.match_id,
                player_a=MatchParticipantContext(
                    player=self._engine_player(players[command.player_a_id])
                ),
                player_b=MatchParticipantContext(
                    player=self._engine_player(players[command.player_b_id])
                ),
                best_of=5, games_to=11, win_by=2,
            )
            anchor = canonical_hash({
                "schema_version": "calendar_match_input_anchor.v1",
                "run_id": run_id, "branch_id": branch_id,
                "calendar": clock.to_metadata(),
                "week": [0, 1],
                "saved_head": revision.saved_head_revision_id,
                "world_fingerprint": world.fingerprint,
                "match_context": match_context.model_dump(mode="json"),
                "seed": command.seed,
            })
            result = MatchEngine(DeterministicRng(command.seed)).simulate(
                match_context, log_anchor_hash=anchor
            )
            match = CalendarStandaloneMatch(
                run_id=run_id, branch_id=branch_id,
                match_id=command.match_id,
                command_id=command.command_id,
                request_fingerprint=request_fp,
                source_saved_head=revision.saved_head_revision_id,
                source_initial_world_fingerprint=world.fingerprint,
                week=RunWeekPosition(calendar=clock, season_index=0, week=1),
                seed=command.seed,
                input_context=match_context,
                result=result,
                operator_label=command.operator_label,
                audit_reason=command.audit_reason,
            )
            put_match(session, match)
            return {"match": match.model_dump(mode="json"), "fingerprint": match.fingerprint}

    def replay(self, *, run_id: str, branch_id: str, match_id: str) -> dict:
        with self.repository._session_factory() as session:
            session.execute(text("BEGIN"))
            rows = load_match_rows(session, run_id=run_id, branch_id=branch_id)
            match = next((state for state in rows if state.match_id == match_id), None)
            if match is None:
                raise KeyError("Calendar match not found")
            # Re-run the actual MatchEngine, not a recomputed summary or
            # manually overwritten Saved payload.
            anchor = canonical_hash({
                "schema_version": "calendar_match_input_anchor.v1",
                "run_id": run_id, "branch_id": branch_id,
                "calendar": match.week.calendar.to_metadata(),
                "week": [0, 1],
                "saved_head": match.source_saved_head,
                "world_fingerprint": match.source_initial_world_fingerprint,
                "match_context": match.input_context.model_dump(mode="json"),
                "seed": match.seed,
            })
            replayed = MatchEngine(DeterministicRng(match.seed)).simulate(
                match.input_context, log_anchor_hash=anchor,
            )
            if canonical_hash(replayed.model_dump(mode="json")) != canonical_hash(
                match.result.model_dump(mode="json")
            ):
                raise ValueError("Calendar match deterministic replay disagrees with stored logs")
            return {
                "match_id": match_id, "fingerprint": match.fingerprint,
                "result": match.result.model_dump(mode="json"),
                "rally_count": len(match.result.rally_log.events),
                "exact_replay": True,
            }
