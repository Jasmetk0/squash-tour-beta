"""Minimum operation-scoped standalone match flow for a canonical empty Run.

This deliberately implements only Master §31.3 acceptance flow #2:
empty Run -> exactly two manually supplied players -> one standalone match.
It does not create Calendar, Tournament, Entry, Draw, Ranking or Week-transition authority.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import ConfigDict, Field, model_validator
from sqlalchemy import select, text

from beta_engine.application.authoritative_slot_matches import AuthoritativeSlotMatchExecutor
from beta_engine.application.initial_world import InitialWorldState
from beta_engine.application.season_player_bootstrap_service import SeasonActivePlayer
from beta_engine.domain.calendar.season_weeks import (
    age_at_calendar_position,
    completed_weeks_at_calendar_position,
    season_week_to_calendar_position,
)
from beta_engine.domain.players.initial_pool import CustomInitialPoolPlayerCreate
from beta_engine.domain.players.models import MAX_RUNTIME_PLAYER_AGE, MIN_RUNTIME_PLAYER_AGE
from beta_engine.domain.rankings.official import FrozenInput, RankingWeek
from beta_engine.domain.simulation_slots import SimulationMatchEventPlan, fingerprint
from beta_engine.infrastructure.db.initial_world_state import get_initial_world, put_initial_world
from beta_engine.infrastructure.db.models import (
    AdoptedTournamentAuthorityModel,
    AuthoritativeSimulationCommandModel,
    PlayerLifecycleWeekStateModel,
    PlayerSportingWeekStateModel,
    RunBranchModel,
    RunContainerModel,
    SimulationEventGroupModel,
    SimulationSlotModel,
    StandaloneMatchWorkspaceModel,
    WeekSimulationScheduleModel,
)
from beta_engine.infrastructure.db.player_lifecycle_state import bootstrap_lifecycle
from beta_engine.infrastructure.db.player_sporting_state import bootstrap_sporting


STANDALONE_EVENT_ID = "standalone-match"
STANDALONE_MATCH_ID = "standalone-match-1"
STANDALONE_GROUP_ID = "standalone-match-group-1"
STANDALONE_SLOT_ID = "standalone-match-slot-1"
STANDALONE_WEEK = RankingWeek(season_index=0, week=1)


class StandaloneMatchWorkspace(FrozenInput):
    schema_version: Literal["standalone_match_workspace.v1"] = "standalone_match_workspace.v1"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    version: int = Field(ge=0)
    players: tuple[CustomInitialPoolPlayerCreate, ...] = ()

    @model_validator(mode="after")
    def canonical_manual_players(self):
        if len(self.players) > 2:
            raise ValueError("Standalone match accepts exactly two manual players at most")
        ids = [player.player_id for player in self.players]
        if any(not player_id for player_id in ids):
            raise ValueError("Standalone manual players require explicit player_id values")
        if len(ids) != len(set(ids)):
            raise ValueError("Standalone manual player IDs must be unique")
        if any(player.created_for_season != "2000/2001" for player in self.players):
            raise ValueError("Standalone pre-alpha match starts in season 2000/2001")
        return self

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.model_dump(mode="json"))


class StandaloneMatchAddPlayerCommand(FrozenInput):
    player: CustomInitialPoolPlayerCreate
    expected_workspace_fingerprint: str | None = None


class StandaloneMatchSimulateCommand(FrozenInput):
    command_id: str = Field(min_length=1, max_length=128)
    expected_workspace_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    seed: int
    operator_label: str = Field(min_length=1, max_length=160)
    audit_reason: str = Field(min_length=1, max_length=1000)


class StandaloneMatchState(FrozenInput):
    schema_version: Literal["standalone_match_state.v1"] = "standalone_match_state.v1"
    run_id: str
    branch_id: str
    workspace: StandaloneMatchWorkspace | None = None
    frozen_world_fingerprint: str | None = None
    result: dict | None = None
    status: Literal["empty", "authoring", "ready", "complete"]


class StandaloneMatchService:
    def __init__(self, session_factory):
        self._session_factory = session_factory

    @staticmethod
    def _load_workspace(session, *, run_id: str, branch_id: str) -> StandaloneMatchWorkspace | None:
        row = session.get(StandaloneMatchWorkspaceModel, (run_id, branch_id))
        if row is None:
            return None
        workspace = StandaloneMatchWorkspace.model_validate_json(row.payload_json)
        if (
            workspace.run_id,
            workspace.branch_id,
            workspace.version,
            workspace.fingerprint,
        ) != (run_id, branch_id, row.version, row.fingerprint):
            raise ValueError("Standalone match workspace identity or fingerprint mismatch")
        return workspace

    @staticmethod
    def _put_workspace(session, workspace: StandaloneMatchWorkspace) -> StandaloneMatchWorkspace:
        row = session.get(StandaloneMatchWorkspaceModel, (workspace.run_id, workspace.branch_id))
        values = {
            "version": workspace.version,
            "fingerprint": workspace.fingerprint,
            "payload_json": workspace.model_dump_json(),
        }
        if row is None:
            row = StandaloneMatchWorkspaceModel(
                run_id=workspace.run_id,
                branch_id=workspace.branch_id,
                **values,
            )
            session.add(row)
        else:
            row.version = values["version"]
            row.fingerprint = values["fingerprint"]
            row.payload_json = values["payload_json"]
        session.flush()
        return workspace

    @staticmethod
    def _validate_scope(session, *, run_id: str, branch_id: str) -> tuple[RunContainerModel, RunBranchModel]:
        run = session.get(RunContainerModel, run_id)
        branch = session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise KeyError("Standalone match Run/Branch scope was not found")
        if run.read_only or branch.read_only:
            raise ValueError("Standalone match requires a writable Run and Branch")
        if branch.status != "active":
            raise ValueError("Standalone match requires an active Branch")
        if run.status not in {"working", "active"}:
            raise ValueError("Standalone match requires a working or active Run")
        return run, branch

    @staticmethod
    def _ensure_operation_scope_is_empty(session, *, run_id: str, branch_id: str) -> None:
        if get_initial_world(session, run_id=run_id, branch_id=branch_id) is not None:
            raise ValueError("Standalone authoring requires a Run/Branch with no InitialWorld")
        if session.scalar(
            select(SimulationSlotModel).where(
                SimulationSlotModel.run_id == run_id,
                SimulationSlotModel.branch_id == branch_id,
            ).limit(1)
        ) is not None:
            raise ValueError("Standalone authoring requires no existing Simulation Slots")
        if session.scalar(
            select(AdoptedTournamentAuthorityModel).where(
                AdoptedTournamentAuthorityModel.run_id == run_id,
                AdoptedTournamentAuthorityModel.branch_id == branch_id,
            ).limit(1)
        ) is not None:
            raise ValueError("Standalone authoring does not attach to Tournament authority")
        if session.scalar(
            select(WeekSimulationScheduleModel).where(
                WeekSimulationScheduleModel.run_id == run_id,
                WeekSimulationScheduleModel.branch_id == branch_id,
            ).limit(1)
        ) is not None:
            raise ValueError("Standalone authoring does not use a Week Simulation Schedule")

    @staticmethod
    def _manual_player_to_active(
        player: CustomInitialPoolPlayerCreate,
        *,
        workspace_fingerprint: str,
        seed: int,
    ) -> SeasonActivePlayer:
        if player.player_id is None:
            raise ValueError("Standalone manual player requires an explicit player_id")
        position = season_week_to_calendar_position(2000, 1)
        age = age_at_calendar_position(
            birth_year=player.birth_year,
            birth_year_week=player.birth_year_week,
            calendar_year=position.calendar_year,
            year_week=position.year_week,
        )
        if not MIN_RUNTIME_PLAYER_AGE <= age <= MAX_RUNTIME_PLAYER_AGE:
            raise ValueError(
                f"Standalone match participant age must be {MIN_RUNTIME_PLAYER_AGE}-{MAX_RUNTIME_PLAYER_AGE} at 2000/01 Week 1"
            )
        age_weeks = completed_weeks_at_calendar_position(
            birth_year=player.birth_year,
            birth_year_week=player.birth_year_week,
            calendar_year=position.calendar_year,
            year_week=position.year_week,
        )
        source_payload = {
            "scope": "standalone-manual-player.v1",
            "workspace": workspace_fingerprint,
            "player": player.model_dump(mode="json"),
        }
        source_fp = hashlib.sha256(
            json.dumps(source_payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        bootstrap_fp = hashlib.sha256(
            f"standalone-bootstrap|{workspace_fingerprint}|{player.player_id}|{seed}|{source_fp}".encode()
        ).hexdigest()
        return SeasonActivePlayer(
            player_id=player.player_id,
            name=player.name,
            country_code=player.country_code,
            nationality=player.nationality or player.country_code,
            birth_year=player.birth_year,
            birth_year_week=player.birth_year_week,
            age_years_at_season_start=age,
            age_weeks_at_season_start=age_weeks,
            current_ability=player.current_ability,
            potential_ability=player.potential_ability,
            potential_tier=player.potential_tier,
            career_stage=player.career_stage,
            play_style=player.play_style,
            archetype=player.archetype,
            attributes=player.attributes,
            hidden_career_traits=player.hidden_career_traits,
            health_status="fresh",
            active_status="active",
            ranking_points=0,
            race_points=0,
            protected_ranking_points=0,
            season="2000/2001",
            source_pool_player_id=player.player_id,
            source_generation_fingerprint=source_fp,
            source_generation="manual",
            manual_override=True,
            locked_from_initial_pool=True,
            bootstrap_fingerprint=bootstrap_fp,
            bootstrap_seed=seed,
            bootstrap_id=f"STANDALONE-{workspace_fingerprint[:16]}",
        )

    @staticmethod
    def _result_payload(group) -> dict:
        result = group.result
        return {
            "schema_version": "standalone_match_commit.v1",
            "event_id": STANDALONE_EVENT_ID,
            "match_id": STANDALONE_MATCH_ID,
            "winner_player_id": result.winner_player_id,
            "loser_player_id": result.loser_player_id,
            "sets_won": dict(result.sets_won),
            "result_fingerprint": group.result_fingerprint,
            "match_input_fingerprint": group.authoritative_input.fingerprint,
            "terminal_sporting_fingerprint": group.terminal_checkpoint.fingerprint,
        }

    def inspect(self, *, run_id: str, branch_id: str) -> StandaloneMatchState:
        with self._session_factory() as session:
            self._validate_scope(session, run_id=run_id, branch_id=branch_id)
            world = get_initial_world(session, run_id=run_id, branch_id=branch_id)
            row = session.get(
                SimulationEventGroupModel,
                (run_id, branch_id, STANDALONE_WEEK.ordinal, STANDALONE_SLOT_ID, STANDALONE_GROUP_ID),
            )
            if row is not None:
                group = AuthoritativeSlotMatchExecutor._load_group(row)
                return StandaloneMatchState(
                    run_id=run_id,
                    branch_id=branch_id,
                    frozen_world_fingerprint=world.fingerprint if world else None,
                    result=self._result_payload(group),
                    status="complete",
                )
            workspace = self._load_workspace(session, run_id=run_id, branch_id=branch_id)
            if world is not None:
                raise ValueError("Standalone state has frozen world truth but no completed standalone match")
            count = len(workspace.players) if workspace else 0
            return StandaloneMatchState(
                run_id=run_id,
                branch_id=branch_id,
                workspace=workspace,
                status="empty" if count == 0 else "ready" if count == 2 else "authoring",
            )

    def add_player(
        self,
        *,
        run_id: str,
        branch_id: str,
        command: StandaloneMatchAddPlayerCommand,
    ) -> StandaloneMatchState:
        with self._session_factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            self._validate_scope(session, run_id=run_id, branch_id=branch_id)
            self._ensure_operation_scope_is_empty(session, run_id=run_id, branch_id=branch_id)
            current = self._load_workspace(session, run_id=run_id, branch_id=branch_id)
            if current is None:
                if command.expected_workspace_fingerprint is not None:
                    raise ValueError("Standalone workspace does not exist at the expected fingerprint")
                current = StandaloneMatchWorkspace(
                    run_id=run_id, branch_id=branch_id, version=0, players=()
                )
            elif (
                command.expected_workspace_fingerprint is not None
                and command.expected_workspace_fingerprint != current.fingerprint
            ):
                raise ValueError("Standalone workspace changed since it was reviewed")
            if len(current.players) >= 2:
                raise ValueError("Standalone workspace already contains two players")
            if command.player.player_id is None:
                raise ValueError("Standalone manual player requires explicit player_id")
            if any(p.player_id == command.player.player_id for p in current.players):
                raise ValueError("Standalone manual player_id already exists in this workspace")
            candidate = StandaloneMatchWorkspace(
                run_id=run_id,
                branch_id=branch_id,
                version=current.version + 1,
                players=(*current.players, command.player),
            )
            # Validate match-engine age bounds before persisting authoring state.
            self._manual_player_to_active(
                command.player,
                workspace_fingerprint=candidate.fingerprint,
                seed=0,
            )
            self._put_workspace(session, candidate)
            return StandaloneMatchState(
                run_id=run_id,
                branch_id=branch_id,
                workspace=candidate,
                status="ready" if len(candidate.players) == 2 else "authoring",
            )

    def simulate(
        self,
        *,
        run_id: str,
        branch_id: str,
        command: StandaloneMatchSimulateCommand,
    ) -> StandaloneMatchState:
        request_fp = fingerprint(
            {
                "scope": [run_id, branch_id],
                "command": command.model_dump(mode="json"),
            }
        )
        with self._session_factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            self._validate_scope(session, run_id=run_id, branch_id=branch_id)
            receipt = session.get(
                AuthoritativeSimulationCommandModel,
                (run_id, branch_id, command.command_id),
            )
            if receipt is not None:
                if receipt.request_fingerprint != request_fp:
                    raise ValueError("Standalone command_id conflicts with an earlier request")
                return StandaloneMatchState.model_validate_json(receipt.result_json)

            self._ensure_operation_scope_is_empty(session, run_id=run_id, branch_id=branch_id)
            workspace = self._load_workspace(session, run_id=run_id, branch_id=branch_id)
            if workspace is None or len(workspace.players) != 2:
                raise ValueError("Standalone simulation requires exactly two reviewed manual players")
            if workspace.fingerprint != command.expected_workspace_fingerprint:
                raise ValueError("Standalone workspace changed since it was reviewed")

            active_players = tuple(
                self._manual_player_to_active(
                    player,
                    workspace_fingerprint=workspace.fingerprint,
                    seed=command.seed,
                )
                for player in workspace.players
            )
            source_fp = hashlib.sha256(
                ("standalone-initial-world|" + workspace.fingerprint).encode()
            ).hexdigest()
            adoption_request_fp = fingerprint(
                {
                    "workspace": workspace.fingerprint,
                    "command_id": command.command_id,
                    "seed": command.seed,
                    "operator_label": command.operator_label,
                    "audit_reason": command.audit_reason,
                }
            )
            world = InitialWorldState(
                run_id=run_id,
                branch_id=branch_id,
                players=tuple(sorted(active_players, key=lambda p: p.player_id)),
                policies=(),
                source_kind="manual_standalone.v1",
                source_season="2000/2001",
                source_fingerprint=source_fp,
                bootstrap_seed=command.seed,
                bootstrap_fingerprint=hashlib.sha256(
                    f"standalone-world-bootstrap|{source_fp}|{command.seed}".encode()
                ).hexdigest(),
                adopted_by_command_id=command.command_id,
                audit_label=command.operator_label,
                audit_reason=command.audit_reason,
                adoption_request_fingerprint=adoption_request_fp,
            )
            put_initial_world(session, world)
            bootstrap_lifecycle(session, world)
            sporting = bootstrap_sporting(session, world)

            event = SimulationMatchEventPlan(
                group_id=STANDALONE_GROUP_ID,
                event_id=STANDALONE_EVENT_ID,
                match_id=STANDALONE_MATCH_ID,
                direct_player_ids=(
                    workspace.players[0].player_id,
                    workspace.players[1].player_id,
                ),
            )
            executor = AuthoritativeSlotMatchExecutor(session)
            slot = executor.create_slot(
                run_id=run_id,
                branch_id=branch_id,
                week=STANDALONE_WEEK,
                slot_id=STANDALONE_SLOT_ID,
                ordinal=1,
                group_ids=(STANDALONE_GROUP_ID,),
                match_events=(event,),
                provenance="Master §31.3 operation-scoped standalone match",
            )
            group = executor.execute_match_group(
                run_id=run_id,
                branch_id=branch_id,
                week=STANDALONE_WEEK,
                slot_id=STANDALONE_SLOT_ID,
                group_id=STANDALONE_GROUP_ID,
                event_id=STANDALONE_EVENT_ID,
                match_id=STANDALONE_MATCH_ID,
                player_a_id=workspace.players[0].player_id,
                player_b_id=workspace.players[1].player_id,
                seed=command.seed,
                expected_slot_start_fingerprint=slot.slot_start_fingerprint,
            )
            if group.authoritative_input.player_projections[0].source_sporting_fingerprint != slot.slot_start_fingerprint:
                raise ValueError("Standalone match did not consume its frozen sporting state")
            if sporting.fingerprint != group.terminal_checkpoint.opening_week_fingerprint:
                raise ValueError("Standalone slot does not open from the frozen Week 1 sporting state")

            session.delete(session.get(StandaloneMatchWorkspaceModel, (run_id, branch_id)))
            result = StandaloneMatchState(
                run_id=run_id,
                branch_id=branch_id,
                frozen_world_fingerprint=world.fingerprint,
                result=self._result_payload(group),
                status="complete",
            )
            session.add(
                AuthoritativeSimulationCommandModel(
                    run_id=run_id,
                    branch_id=branch_id,
                    command_id=command.command_id,
                    request_fingerprint=request_fp,
                    status="complete",
                    result_json=result.model_dump_json(),
                )
            )
            session.flush()
            return result
