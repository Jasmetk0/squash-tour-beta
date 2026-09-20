"""Run/Branch-owned orchestration over the authoritative Simulation Slot ledger.

Canonical Run-owned Draw authority is the preferred tournament topology source.
Legacy MatchPackage data remains a temporary execution/result payload and historical
compatibility reader; legacy producer files are not execution state.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Literal

from pydantic import Field
from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

from beta_engine.application.authoritative_slot_matches import (
    AuthoritativeTournamentResult,
    AuthoritativeSlotMatchExecutor,
    build_authoritative_tournament_ranking_packages,
    build_run_owned_tournament_authorities,
    validate_adopted_four_player_match_package,
)
from beta_engine.application.canonical_tournament_topology import (
    project_canonical_draw_to_match_topology,
)
from beta_engine.application.final_season_transition import (
    FinalSeasonTransitionCommand,
    FinalSeasonTransitionResult,
    commit_final_season_transition,
)
from beta_engine.application.ordinary_season_transition import (
    OrdinarySeasonTransitionCommand,
    OrdinarySeasonTransitionResult,
    commit_ordinary_season_transition,
)
from beta_engine.application.season_closing_ranking_resolution import (
    resolve_canonical_season_closing_ranking,
)
from beta_engine.application.season_transition_configuration import (
    resolve_season_transition_configuration,
)
from beta_engine.application.season_transition_lifecycle import (
    resolve_season_transition_lifecycle,
)
from beta_engine.application.season_transition_ranking import (
    resolve_season_transition_ranking,
)
from beta_engine.application.season_transition_sporting import (
    resolve_season_transition_sporting,
)
from beta_engine.application.run_owned_match_package import (
    build_run_owned_match_package,
)
from beta_engine.application.ranking_tournament_ingestion import (
    TournamentRankingBinding,
    prepare_canonical_tournament_ranking_sources,
    prepare_final_season_closing_ranking_results,
    prepare_tournament_ranking_sources,
)
from beta_engine.application.season_match_service import (
    FrozenQualifierPromotion,
    SeasonEventMatchPackage,
    SeasonMatchService,
)
from beta_engine.application.season_point_awards_service import (
    FrozenPointAwardAuthority,
    SeasonPointAwardsService,
)
from beta_engine.domain.rankings.official import FrozenInput, RankingWeek
from beta_engine.domain.rankings.tournament_source import OwnedTournamentRankingSource
from beta_engine.domain.tournaments.models import CalendarEvent
from beta_engine.domain.simulation_slots import (
    SimulationMatchEventPlan,
    WeekSimulationSchedule,
    WeekSimulationScheduleSlot,
    fingerprint,
)
from beta_engine.infrastructure.db.models import (
    AuthoritativeSimulationCommandModel,
    AuthoritativeWorldStateModel,
    AdoptedTournamentAuthorityModel,
    BranchSavedRevisionModel,
    BranchWorkingDraftModel,
    PlayerSportingWeekStateModel,
    RankingTransitionAuthorityModel,
    RunBranchModel,
    RunContainerModel,
    SimulationEventGroupModel,
    SimulationSlotModel,
    TournamentDrawAuthorityModel,
    WeekSimulationScheduleModel,
)
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)
from beta_engine.infrastructure.db.tournament_draw_authority import (
    TournamentDrawAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_walkover_authority import (
    TournamentWalkoverAuthorityStore,
)
from beta_engine.infrastructure.db.player_lifecycle_state import get_lifecycle
from beta_engine.infrastructure.db.player_sporting_state import (
    get_sporting,
    preflight_completed_context_from_authoritative_matches,
)
from beta_engine.infrastructure.db.authoritative_week_transition import (
    preview_persisted_week_transition,
)


class AuthoritativeSimulationCommand(FrozenInput):
    command_id: str = Field(min_length=1, max_length=128)
    run_id: str
    branch_id: str
    expected_week: RankingWeek
    expected_position_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_revision_id: str = Field(min_length=1)
    group_id: str | None = None

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.model_dump(mode="json"))


class AuthoritativeWalkoverCommand(FrozenInput):
    command_id: str = Field(min_length=1, max_length=128)
    run_id: str
    branch_id: str
    expected_week: RankingWeek
    expected_position_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_revision_id: str = Field(min_length=1)
    group_id: str = Field(min_length=1)
    withdrawn_player_id: str = Field(min_length=1)

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.model_dump(mode="json"))


class _AdoptedTournamentEvidence(FrozenInput):
    """One immutable tournament entry inside adopted week authority."""

    event_id: str = Field(min_length=1)
    package: SeasonEventMatchPackage | None = None
    calendar_event: CalendarEvent | None = None
    point_award_authority: FrozenPointAwardAuthority | None = None
    draw_authority_fingerprint: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )


class AuthoritativeSeasonTransitionPreflight(FrozenInput):
    schema_version: Literal["authoritative_season_transition_preflight.v1"] = (
        "authoritative_season_transition_preflight.v1"
    )
    run_id: str
    branch_id: str
    completed_week: RankingWeek
    target_week: RankingWeek | None
    final_season: bool
    saved_revision_id: str | None
    draft_version: int | None = None
    default_closing_ranking_fingerprint: str | None = None
    default_configuration_fingerprint: str | None = None
    default_sporting_fingerprint: str | None = None
    default_lifecycle_fingerprint: str | None = None
    default_ranking_fingerprint: str | None = None
    position_fingerprint: str
    state_blockers: tuple[str, ...] = ()
    implementation_gaps: tuple[str, ...] = ()
    ready_for_execution: bool = False
    preflight_fingerprint: str


class AuthoritativeSimulationPosition(FrozenInput):
    run_id: str
    branch_id: str
    current_week: RankingWeek
    current_slot_id: str | None
    slot_ordinal: int | None
    unresolved_group_ids: tuple[str, ...]
    eligible_match_ids: tuple[str, ...]
    blocked_match_ids: tuple[str, ...]
    current_slot_complete: bool
    supported_tournament_complete: bool
    week_ready_for_transition: bool
    transition_blockers: tuple[str, ...] = ()
    terminal_sporting_fingerprint: str | None
    position_fingerprint: str


@dataclass(slots=True)
class AuthoritativeRunSimulationDriver:
    factory: sessionmaker[Session]
    match_service: SeasonMatchService
    awards_service: SeasonPointAwardsService

    def position(
        self, *, run_id: str, branch_id: str
    ) -> AuthoritativeSimulationPosition:
        with self.factory() as session:
            return self._position(session, run_id, branch_id)

    def season_transition_preflight(
        self, *, run_id: str, branch_id: str
    ) -> AuthoritativeSeasonTransitionPreflight:
        with self.factory() as session:
            return self._season_transition_preflight(session, run_id, branch_id)

    def _season_transition_preflight(
        self, session: Session, run_id: str, branch_id: str
    ) -> AuthoritativeSeasonTransitionPreflight:
        position = self._position(session, run_id, branch_id)
        week = position.current_week
        branch = session.get(RunBranchModel, branch_id)
        draft = session.scalar(
            select(BranchWorkingDraftModel).where(
                BranchWorkingDraftModel.branch_id == branch_id
            )
        )
        blockers = [
            item
            for item in position.transition_blockers
            if item != "season_transition_required"
        ]
        if week.week != 61:
            blockers.append("not_at_season_boundary")
        if branch is None or draft is None or branch.run_id != run_id:
            blockers.append("run_branch_scope_missing")
        else:
            if branch.read_only or branch.status != "active":
                blockers.append("run_branch_not_writable")
            if draft.status != "clean":
                blockers.append("working_draft_dirty")
            if (
                not branch.saved_head_revision_id
                or draft.base_revision_id != branch.saved_head_revision_id
            ):
                blockers.append("saved_revision_head_mismatch")

        at_boundary = week.week == 61
        final_season = at_boundary and week.season_index == 49
        target_week = (
            RankingWeek(season_index=week.season_index + 1, week=1)
            if at_boundary and not final_season
            else None
        )
        default_closing = None
        if at_boundary:
            try:
                default_closing = resolve_canonical_season_closing_ranking(
                    session,
                    run_id=run_id,
                    branch_id=branch_id,
                    completed_week=week,
                )
            except ValueError:
                blockers.append("season_closing_ranking_unavailable")
        default_configuration = None
        default_sporting = None
        default_lifecycle = None
        default_ranking = None
        if target_week is not None:
            try:
                default_configuration = resolve_season_transition_configuration(
                    session,
                    run_id=run_id,
                    branch_id=branch_id,
                )
            except ValueError:
                blockers.append("season_transition_configuration_unavailable")
            if default_configuration is not None:
                try:
                    default_sporting = resolve_season_transition_sporting(
                        session,
                        default_configuration,
                    )
                except ValueError:
                    blockers.append("season_transition_sporting_unavailable")
                try:
                    default_lifecycle = resolve_season_transition_lifecycle(
                        session,
                        default_configuration,
                    )
                except ValueError:
                    blockers.append("season_transition_lifecycle_unavailable")
                if default_lifecycle is not None:
                    try:
                        default_ranking = resolve_season_transition_ranking(
                            session,
                            default_configuration,
                        )
                    except ValueError:
                        blockers.append("season_transition_ranking_unavailable")
        implementation_gaps = ()
        state_blockers = tuple(dict.fromkeys(blockers))
        body = {
            "scope": [run_id, branch_id],
            "completed_week": week.model_dump(mode="json"),
            "target_week": target_week.model_dump(mode="json")
            if target_week
            else None,
            "final_season": final_season,
            "saved_revision_id": branch.saved_head_revision_id
            if branch
            else None,
            "draft_version": draft.draft_version if draft else None,
            "default_closing_ranking_fingerprint": (
                default_closing.fingerprint if default_closing else None
            ),
            "default_configuration_fingerprint": (
                default_configuration.fingerprint if default_configuration else None
            ),
            "default_sporting_fingerprint": (
                default_sporting.target_state.fingerprint if default_sporting else None
            ),
            "default_lifecycle_fingerprint": (
                default_lifecycle.target_state.fingerprint if default_lifecycle else None
            ),
            "default_ranking_fingerprint": (
                default_ranking.target_snapshot.fingerprint if default_ranking else None
            ),
            "position_fingerprint": position.position_fingerprint,
            "state_blockers": state_blockers,
            "implementation_gaps": implementation_gaps,
        }
        ready = not state_blockers and not implementation_gaps
        return AuthoritativeSeasonTransitionPreflight(
            run_id=run_id,
            branch_id=branch_id,
            completed_week=week,
            target_week=target_week,
            final_season=final_season,
            saved_revision_id=branch.saved_head_revision_id
            if branch
            else None,
            draft_version=draft.draft_version if draft else None,
            default_closing_ranking_fingerprint=(
                default_closing.fingerprint if default_closing else None
            ),
            default_configuration_fingerprint=(
                default_configuration.fingerprint if default_configuration else None
            ),
            default_sporting_fingerprint=(
                default_sporting.target_state.fingerprint if default_sporting else None
            ),
            default_lifecycle_fingerprint=(
                default_lifecycle.target_state.fingerprint if default_lifecycle else None
            ),
            default_ranking_fingerprint=(
                default_ranking.target_snapshot.fingerprint if default_ranking else None
            ),
            position_fingerprint=position.position_fingerprint,
            state_blockers=state_blockers,
            implementation_gaps=implementation_gaps,
            ready_for_execution=ready,
            preflight_fingerprint=fingerprint(body),
        )

    def advance_season(
        self, command: OrdinarySeasonTransitionCommand
    ) -> OrdinarySeasonTransitionResult:
        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            existing = session.get(
                BranchSavedRevisionModel,
                command.season_saved_revision_id,
            )
            if existing is not None:
                return commit_ordinary_season_transition(session, command)

            preflight = self._season_transition_preflight(
                session, command.run_id, command.branch_id
            )
            if preflight.preflight_fingerprint != command.expected_preflight_fingerprint:
                raise ValueError("season transition preflight is stale")
            if preflight.final_season or preflight.target_week is None:
                raise ValueError(
                    "ordinary Season Transition requires a non-final Week 61 boundary"
                )
            if not preflight.ready_for_execution:
                raise ValueError(
                    "ordinary Season Transition preflight is not ready: "
                    + ", ".join(
                        (*preflight.state_blockers, *preflight.implementation_gaps)
                    )
                )
            if preflight.saved_revision_id != command.expected_saved_revision_id:
                raise ValueError("Season Transition Saved Revision head is stale")
            if preflight.draft_version != command.expected_draft_version:
                raise ValueError("Season Transition Working Draft version is stale")
            if (
                command.configuration.completed_week != preflight.completed_week
                or command.configuration.target_week != preflight.target_week
            ):
                raise ValueError("Season Transition configuration boundary is stale")
            return commit_ordinary_season_transition(session, command)

    def finalize_final_season(
        self, command: FinalSeasonTransitionCommand
    ) -> FinalSeasonTransitionResult:
        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            existing = session.get(
                BranchSavedRevisionModel,
                command.final_saved_revision_id,
            )
            if existing is not None:
                return commit_final_season_transition(session, command)

            preflight = self._season_transition_preflight(
                session, command.run_id, command.branch_id
            )
            if preflight.preflight_fingerprint != command.expected_preflight_fingerprint:
                raise ValueError("season transition preflight is stale")
            if not preflight.final_season:
                raise ValueError("final season closure requires 2049/50 Week 61")
            if not preflight.ready_for_execution:
                raise ValueError(
                    "final season closure preflight is not ready: "
                    + ", ".join(
                        (*preflight.state_blockers, *preflight.implementation_gaps)
                    )
                )
            if preflight.saved_revision_id != command.expected_saved_revision_id:
                raise ValueError("final season closure Saved Revision head is stale")
            if preflight.draft_version != command.expected_draft_version:
                raise ValueError("final season closure Working Draft version is stale")
            return commit_final_season_transition(session, command)

    def simulate_next_match(self, command: AuthoritativeSimulationCommand):
        return self._mutate(command, mode="match")

    def simulate_next_slot(
        self, command: AuthoritativeSimulationCommand, *, fault_at: str | None = None
    ):
        return self._mutate(command, mode="slot", fault_at=fault_at)

    def commit_post_cutoff_walkover(self, command: AuthoritativeWalkoverCommand):
        """Commit one Master §15.9 W/O without simulating a competitive match.

        W/O remains noncompetitive sporting evidence, but if it resolves the final
        outstanding tournament node the normal canonical close now freezes result
        and point authorities from the reached-stage progression.
        """

        request_fp = fingerprint(
            {"mode": "walkover", "command": command.model_dump(mode="json")}
        )
        key = (command.run_id, command.branch_id, command.command_id)
        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            self._require_writable_scope(session, command.run_id, command.branch_id)
            receipt = session.get(AuthoritativeSimulationCommandModel, key)
            if receipt is not None:
                if receipt.request_fingerprint != request_fp:
                    raise ValueError(
                        "simulation command ID already has a different request"
                    )
                if receipt.status != "complete":
                    raise ValueError("walkover command receipt is incomplete")
                return json.loads(receipt.result_json)

            before = self._position(session, command.run_id, command.branch_id)
            self._validate_expected(session, command, before)
            packages, authority_fp = self._authority_package(
                session,
                command.run_id,
                command.branch_id,
                before.current_week,
                adopt=True,
            )
            self._ensure_current_slot(session, command, packages)
            current = self._position(session, command.run_id, command.branch_id)
            if current.current_slot_id is None:
                raise ValueError("walkover target has no current Simulation Slot")
            eligible_groups = self._eligible_groups(
                session, current, packages
            )
            if command.group_id not in eligible_groups:
                raise ValueError(
                    "walkover target is completed, blocked, or outside the current slot"
                )

            slot = session.get(
                SimulationSlotModel,
                (
                    command.run_id,
                    command.branch_id,
                    command.expected_week.ordinal,
                    current.current_slot_id,
                ),
            )
            if slot is None:
                raise ValueError("walkover current Simulation Slot disappeared")
            plan = AuthoritativeSlotMatchExecutor._load_plan(slot)
            try:
                event_plan = next(
                    item
                    for item in plan.match_events
                    if item.group_id == command.group_id
                )
            except StopIteration as exc:
                raise ValueError("walkover target group is not planned") from exc

            result = TournamentWalkoverAuthorityStore(session).commit(
                run_id=command.run_id,
                branch_id=command.branch_id,
                week=command.expected_week,
                event_id=event_plan.event_id,
                command_id=command.command_id,
                withdrawn_player_id=command.withdrawn_player_id,
                slot_id=slot.slot_id,
                group_id=command.group_id,
            )
            self._advance_or_close(session, command, packages)
            after = self._position(session, command.run_id, command.branch_id)
            payload = {
                "walkover": {
                    "authority_fingerprint": result.authoritative_input.fingerprint,
                    "result_fingerprint": result.result_fingerprint,
                    "event_id": result.authoritative_input.event_id,
                    "match_id": result.result.match_id,
                    "winner_player_id": result.result.winner_player_id,
                    "withdrawn_player_id": result.result.loser_player_id,
                    "scoreline": result.result.scoreline,
                },
                "position": after.model_dump(mode="json"),
                "authority_fingerprint": authority_fp,
            }
            session.add(
                AuthoritativeSimulationCommandModel(
                    run_id=command.run_id,
                    branch_id=command.branch_id,
                    command_id=command.command_id,
                    request_fingerprint=request_fp,
                    status="complete",
                    result_json=json.dumps(
                        payload, sort_keys=True, separators=(",", ":")
                    ),
                )
            )
            session.flush()
            return payload

    def _mutate(self, command, *, mode: Literal["match", "slot"], fault_at=None):
        request_fp = fingerprint(
            {"mode": mode, "command": command.model_dump(mode="json")}
        )
        # Establish one durable operation receipt and materialize the frozen slot
        # before executing groups. Each independent group then owns its transaction.
        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            self._require_writable_scope(session, command.run_id, command.branch_id)
            key = (command.run_id, command.branch_id, command.command_id)
            receipt = session.get(AuthoritativeSimulationCommandModel, key)
            if receipt:
                if receipt.request_fingerprint != request_fp:
                    raise ValueError(
                        "simulation command ID already has a different request"
                    )
                if receipt.status == "complete":
                    return json.loads(receipt.result_json)
                operation_targets = tuple(
                    json.loads(receipt.result_json)["target_group_ids"]
                )
            else:
                before = self._position(session, command.run_id, command.branch_id)
                self._validate_expected(session, command, before)
                packages, authority_fp = self._authority_package(
                    session,
                    command.run_id,
                    command.branch_id,
                    before.current_week,
                    adopt=True,
                )
                self._ensure_current_slot(session, command, packages)
                position = self._position(session, command.run_id, command.branch_id)
                targets = self._targets(session, command, mode, position, packages)
                operation_targets = targets
                session.add(
                    AuthoritativeSimulationCommandModel(
                        run_id=command.run_id,
                        branch_id=command.branch_id,
                        command_id=command.command_id,
                        request_fingerprint=request_fp,
                        status="pending",
                        result_json=json.dumps(
                            {
                                "target_group_ids": targets,
                                "authority_fingerprint": authority_fp,
                            }
                        ),
                    )
                )

        for index, group_id in enumerate(operation_targets):
            if fault_at == "before_second_group" and index == 1:
                raise RuntimeError("fault before second group")
            with self.factory.begin() as session:
                session.execute(text("BEGIN IMMEDIATE"))
                self._require_writable_scope(session, command.run_id, command.branch_id)
                packages = self._pending_package(session, command, request_fp)
                current = self._position(session, command.run_id, command.branch_id)
                if group_id in current.unresolved_group_ids:
                    self._execute_group(session, command, packages, group_id)
            if fault_at == "after_first_group" and index == 0:
                raise RuntimeError("fault after first committed group")

        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            self._require_writable_scope(session, command.run_id, command.branch_id)
            packages = self._pending_package(session, command, request_fp)
            self._advance_or_close(session, command, packages, fault_at=fault_at)
            after = self._position(session, command.run_id, command.branch_id)
            payload = after.model_dump(mode="json")
            receipt = session.get(AuthoritativeSimulationCommandModel, key)
            if receipt is None:
                raise ValueError("pending simulation command receipt disappeared")
            receipt.status = "complete"
            receipt.result_json = json.dumps(
                payload, sort_keys=True, separators=(",", ":")
            )
            if fault_at == "after_source_staging_before_receipt":
                raise RuntimeError(
                    "fault after ranking source staging before command receipt"
                )
            return payload

    def _pending_package(self, session, command, request_fp):
        receipt = session.get(
            AuthoritativeSimulationCommandModel,
            (command.run_id, command.branch_id, command.command_id),
        )
        if (
            receipt is None
            or receipt.request_fingerprint != request_fp
            or receipt.status != "pending"
        ):
            raise ValueError("pending simulation command receipt is invalid")
        evidence = json.loads(receipt.result_json)
        packages, authority_fp = self._authority_package(
            session,
            command.run_id,
            command.branch_id,
            command.expected_week,
            adopt=False,
        )
        if evidence.get("authority_fingerprint") != authority_fp:
            raise ValueError("pending command tournament authority changed")
        slot = session.scalar(
            select(SimulationSlotModel).where(
                SimulationSlotModel.run_id == command.run_id,
                SimulationSlotModel.branch_id == command.branch_id,
                SimulationSlotModel.week_ordinal == command.expected_week.ordinal,
                SimulationSlotModel.status != "complete",
            )
        )
        if (
            slot is not None
            and authority_fp
            not in AuthoritativeSlotMatchExecutor._load_plan(slot).provenance
        ):
            raise ValueError("pending command slot authority is incoherent")
        return packages

    @staticmethod
    def _require_writable_scope(session, run_id, branch_id):
        run = session.get(RunContainerModel, run_id)
        branch = session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("authoritative simulation Run/Branch scope does not exist")
        if run.read_only or branch.read_only or branch.status != "active":
            raise ValueError("authoritative simulation Run/Branch is not writable")

    @staticmethod
    def _validate_expected(session, command, before):
        if before.current_week != command.expected_week:
            raise ValueError("expected current week is stale")
        if before.position_fingerprint != command.expected_position_fingerprint:
            raise ValueError("simulation position is stale")
        branch = session.get(RunBranchModel, command.branch_id)
        if (
            branch is None
            or branch.run_id != command.run_id
            or branch.saved_head_revision_id != command.expected_revision_id
        ):
            raise ValueError("expected Branch head is stale")

    def _targets(self, session, command, mode, position, package):
        eligible_groups = self._eligible_groups(session, position, package)
        if mode == "match":
            if command.group_id is None:
                if len(eligible_groups) != 1:
                    raise ValueError("an explicit current-slot group_id is required")
                return eligible_groups
            if command.group_id not in eligible_groups:
                raise ValueError(
                    "target is completed, blocked, or outside the current slot"
                )
            return (command.group_id,)
        if command.group_id is not None:
            raise ValueError("Simulate Next Slot does not accept group_id")
        if not eligible_groups:
            raise ValueError("current slot has no unresolved eligible match")
        return eligible_groups

    def _current_week(self, session, run_id, branch_id):
        world = session.get(AuthoritativeWorldStateModel, (run_id, branch_id))
        if world:
            return RankingWeek(
                season_index=world.current_ordinal // 61,
                week=world.current_ordinal % 61 + 1,
            )
        rows = session.execute(
            select(PlayerSportingWeekStateModel.week_ordinal)
            .where(
                PlayerSportingWeekStateModel.run_id == run_id,
                PlayerSportingWeekStateModel.branch_id == branch_id,
            )
            .order_by(PlayerSportingWeekStateModel.week_ordinal.desc())
        ).first()
        if not rows:
            raise ValueError("authoritative sporting week state is missing")
        ordinal = rows[0]
        return RankingWeek(season_index=ordinal // 61, week=ordinal % 61 + 1)

    def _canonical_draw_binding(
        self,
        session,
        *,
        run_id,
        branch_id,
        week,
        event_id,
    ):
        """Resolve Draw ownership as frozen by adopted tournament authority."""

        adopted = session.get(
            AdoptedTournamentAuthorityModel,
            (run_id, branch_id, week.ordinal),
        )
        expected_fp = None
        binding_frozen = False
        if adopted is not None:
            items = self._decode_adopted_authority(adopted.package_json)
            matches = [
                item.draw_authority_fingerprint
                for item in items
                if item.event_id == event_id
            ]
            if len(matches) != 1:
                raise ValueError(
                    "frozen tournament authority lacks unique event Draw binding"
                )
            expected_fp = matches[0]
            binding_frozen = True

        draw = TournamentDrawAuthorityStore(session).get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if binding_frozen:
            if expected_fp is None:
                return None
            if draw is None or draw.fingerprint != expected_fp:
                raise ValueError(
                    "frozen tournament authority canonical Draw binding changed"
                )
            return draw
        return draw

    def _replay_adopted_authority(
        self,
        session,
        *,
        run_id,
        branch_id,
        week,
        row,
    ):
        items = self._decode_adopted_authority(row.package_json)
        packages = []
        draw_store = TournamentDrawAuthorityStore(session)
        for item in items:
            if item.package is not None:
                package = item.package
                if package.event_id != item.event_id:
                    raise ValueError(
                        "historical frozen tournament authority event identity changed"
                    )
                if item.draw_authority_fingerprint is not None:
                    draw = draw_store.get(
                        run_id=run_id,
                        branch_id=branch_id,
                        event_id=item.event_id,
                    )
                    if (
                        draw is None
                        or draw.fingerprint != item.draw_authority_fingerprint
                    ):
                        raise ValueError(
                            "frozen tournament authority canonical Draw binding changed"
                        )
                packages.append(package)
                continue

            if (
                item.calendar_event is None
                or item.point_award_authority is None
                or item.draw_authority_fingerprint is None
            ):
                raise ValueError(
                    "canonical frozen tournament authority is incomplete"
                )
            event = item.calendar_event
            if event.event_id != item.event_id or event.season_week != week.week:
                raise ValueError(
                    "canonical frozen tournament Calendar Event scope changed"
                )
            expected_start = 2000 + week.season_index
            expected_season = f"{expected_start}/{expected_start + 1}"
            event_season_matches = (
                event.season == expected_start
                if isinstance(event.season, int)
                else str(event.season) == expected_season
            )
            if not event_season_matches:
                raise ValueError(
                    "canonical frozen tournament Calendar Event season changed"
                )
            draw = draw_store.get(
                run_id=run_id,
                branch_id=branch_id,
                event_id=item.event_id,
            )
            if draw is None or draw.fingerprint != item.draw_authority_fingerprint:
                raise ValueError(
                    "frozen tournament authority canonical Draw binding changed"
                )
            package = build_run_owned_match_package(
                draw=draw,
                event=event,
                week=week,
            )
            packages.append(
                self._bind_owned_draw_evidence(
                    package=package,
                    draw=draw,
                    week=week,
                )
            )

        authority_fp = self._tournament_authority_fingerprint(
            run_id,
            branch_id,
            week,
            items,
        )
        if authority_fp != row.authority_fingerprint:
            raise ValueError("frozen tournament authority is corrupt")
        return tuple(sorted(packages, key=lambda package: package.event_id)), authority_fp

    def _packages(
        self,
        week,
        *,
        required=True,
        session=None,
        run_id=None,
        branch_id=None,
    ):
        season = f"{2000 + week.season_index}/{2001 + week.season_index}"

        if session is not None and run_id is not None and branch_id is not None:
            adopted = session.get(
                AdoptedTournamentAuthorityModel,
                (run_id, branch_id, week.ordinal),
            )
            if adopted is not None:
                packages, _ = self._replay_adopted_authority(
                    session,
                    run_id=run_id,
                    branch_id=branch_id,
                    week=week,
                    row=adopted,
                )
                if not packages and required:
                    raise ValueError("supported tournament authority is missing")
                return packages

        canonical_packages = {}
        canonical_event_ids = set()
        if session is not None and run_id is not None and branch_id is not None:
            draw_event_ids = tuple(
                session.scalars(
                    select(TournamentDrawAuthorityModel.event_id)
                    .where(
                        TournamentDrawAuthorityModel.run_id == run_id,
                        TournamentDrawAuthorityModel.branch_id == branch_id,
                    )
                    .order_by(TournamentDrawAuthorityModel.event_id)
                ).all()
            )
            if draw_event_ids:
                calendar = self.awards_service.calendar_service.get_calendar(
                    season=season
                ).calendar
                if calendar is None:
                    raise ValueError(
                        "canonical Draw execution requires the season Calendar authority"
                    )
                events = {event.event_id: event for event in calendar.events}
                for event_id in draw_event_ids:
                    event = events.get(event_id)
                    if event is None or event.season_week != week.week:
                        continue
                    draw = self._canonical_draw_binding(
                        session,
                        run_id=run_id,
                        branch_id=branch_id,
                        week=week,
                        event_id=event_id,
                    )
                    if draw is None:
                        continue
                    package = build_run_owned_match_package(
                        draw=draw,
                        event=event,
                        week=week,
                    )
                    canonical_packages[event_id] = self._bind_owned_draw_evidence(
                        package=package,
                        draw=draw,
                        week=week,
                    )
                    canonical_event_ids.add(event_id)

        legacy_packages = tuple(
            sorted(
                (
                    p
                    for p in self.match_service._load_registry().matches_by_event_id.values()
                    if p.season == season
                    and p.season_week == week.week
                    and p.event_id not in canonical_event_ids
                ),
                key=lambda package: package.event_id,
            )
        )
        bound_legacy = []
        for package in legacy_packages:
            canonical = None
            if session is not None and run_id is not None and branch_id is not None:
                canonical = self._canonical_draw_binding(
                    session,
                    run_id=run_id,
                    branch_id=branch_id,
                    week=week,
                    event_id=package.event_id,
                )
            if canonical is not None:
                if package.event_id not in canonical_packages:
                    raise ValueError(
                        "canonical Draw event could not build Run-owned MatchPackage"
                    )
                continue
            bound_legacy.append(self._bind_current_draw_evidence(package, week))

        packages = tuple(
            sorted(
                (*canonical_packages.values(), *bound_legacy),
                key=lambda package: package.event_id,
            )
        )
        if not packages and required:
            raise ValueError("supported tournament authority is missing")
        if session is None:
            for package in packages:
                self._topology((package,))
        return packages

    def _bind_owned_draw_evidence(self, *, package, draw, week):
        """Bind MatchPackage execution payload to canonical Run-owned Draw authority."""
        expected_season = f"{2000 + week.season_index}/{2001 + week.season_index}"
        if (
            package.event_id != draw.event_id
            or package.season != expected_season
            or package.season_week != week.week
        ):
            raise ValueError("canonical Draw/MatchPackage event or week identity conflicts")
        projected = package.model_copy(deep=True)
        topology = project_canonical_draw_to_match_topology(
            draw=draw,
            package=projected,
        )
        bye_winners = dict(topology.bye_winners)
        for match in projected.qualification_matches + projected.main_draw_matches:
            winner = bye_winners.get(match.match_id)
            if winner is None:
                continue
            match.winner_player_id = winner
            match.loser_player_id = None
            match.scoreline = "BYE"
            match.status = "completed"
            match.result_notes = "automatic BYE advance from canonical Draw authority"
            match.result_fingerprint = fingerprint(
                {
                    "action": "canonical_draw_bye_advance.v1",
                    "draw_authority_fingerprint": draw.fingerprint,
                    "event_id": projected.event_id,
                    "match_id": match.match_id,
                    "winner_player_id": winner,
                }
            )
        return projected.model_copy(
            update={
                "frozen_qualifier_promotions": list(topology.qualifier_promotions),
                "frozen_bye_match_ids": list(topology.bye_match_ids),
            }
        )

    def _bind_current_draw_evidence(self, package, week):
        """Validate producer lineage and freeze qualification side mappings."""
        package = package.model_copy(deep=True)
        legacy_completed = bool(package.main_draw_matches) and all(
            item.status == "completed"
            for item in package.qualification_matches + package.main_draw_matches
        )
        draw = self.match_service.draw_service.get_draw_package(
            event_id=package.event_id
        ).draw_package
        if draw is None:
            if legacy_completed:
                return package
            raise ValueError("persisted DrawPackage authority is missing")
        entry = self.match_service.draw_service.entry_list_service.get_entry_list(
            event_id=package.event_id
        ).entry_list
        if entry is None:
            if legacy_completed:
                return package
            raise ValueError("persisted EntryList authority is missing")
        expected_season = f"{2000 + week.season_index}/{2001 + week.season_index}"
        if not legacy_completed and (
            package.event_id != draw.event_id
            or package.season != draw.season
            or package.season != expected_season
            or package.season_week != draw.season_week
            or package.season_week != week.week
        ):
            raise ValueError("persisted Match/Draw event or week identity conflicts")
        if package.metadata.draw_package_fingerprint != draw.metadata.build_fingerprint:
            raise ValueError("persisted MatchPackage DrawPackage fingerprint conflicts")
        if draw.metadata.entry_list_fingerprint != entry.metadata.build_fingerprint:
            raise ValueError("persisted DrawPackage EntryList fingerprint conflicts")
        bracket_fingerprints = {
            "main": draw.main_draw.generated_fingerprint,
            "qualification": (
                draw.qualification_draw.generated_fingerprint
                if draw.qualification_draw
                else None
            ),
        }
        for match in package.qualification_matches + package.main_draw_matches:
            if match.source_draw_fingerprint != bracket_fingerprints[
                match.draw_type
            ] and not legacy_completed:
                raise ValueError("persisted match source Draw fingerprint conflicts")

        if not legacy_completed:
            frozen_late = sorted(
                package.frozen_late_replacements,
                key=lambda item: item.target_slot_id,
            )
            expected_late_fp = (
                fingerprint(
                    [item.model_dump(mode="json") for item in frozen_late]
                )
                if frozen_late
                else None
            )
            if package.metadata.late_replacements_fingerprint != expected_late_fp:
                raise ValueError(
                    "persisted MatchPackage late-replacement fingerprint conflicts"
                )
            draw_slots = {
                slot.slot_id: slot for slot in draw.main_draw.slots
            }
            observed_fingerprints: list[str] = []
            for replacement in frozen_late:
                if (
                    replacement.draw_package_fingerprint
                    != draw.metadata.build_fingerprint
                    or replacement.entry_list_fingerprint
                    != entry.metadata.build_fingerprint
                ):
                    raise ValueError(
                        "persisted late-replacement producer lineage conflicts"
                    )
                slot = draw_slots.get(replacement.target_slot_id)
                if (
                    slot is None
                    or slot.player_id != replacement.withdrawn_player_id
                    or slot.bracket_position
                    != replacement.target_bracket_position
                ):
                    raise ValueError(
                        "persisted late-replacement target conflicts with Draw authority"
                    )
                targets = [
                    (match, side)
                    for match in package.main_draw_matches
                    for side in ("top", "bottom")
                    if getattr(match, f"{side}_slot_id")
                    == replacement.target_slot_id
                ]
                if len(targets) != 1:
                    raise ValueError(
                        "persisted late-replacement Match side is ambiguous"
                    )
                target, side = targets[0]
                if (
                    getattr(target, f"{side}_player_id")
                    != replacement.replacement_player_id
                    or getattr(
                        target,
                        f"{side}_late_replacement_fingerprint",
                    )
                    != replacement.authority_fingerprint
                ):
                    raise ValueError(
                        "persisted late-replacement Match evidence conflicts"
                    )
                observed_fingerprints.append(replacement.authority_fingerprint)

            all_side_fingerprints = sorted(
                fingerprint_value
                for match in package.main_draw_matches
                for fingerprint_value in (
                    match.top_late_replacement_fingerprint,
                    match.bottom_late_replacement_fingerprint,
                )
                if fingerprint_value is not None
            )
            if all_side_fingerprints != sorted(observed_fingerprints):
                raise ValueError(
                    "persisted MatchPackage has orphan late-replacement evidence"
                )

        promotions = []
        if package.qualification_matches:
            final_round = max(m.round_number for m in package.qualification_matches)
            finals = sorted(
                (
                    m
                    for m in package.qualification_matches
                    if m.round_number == final_round
                ),
                key=lambda m: (m.bracket_position, m.match_id),
            )
            placeholders = sorted(
                draw.main_draw.qualifier_placeholders,
                key=lambda p: (p.qualifier_index, p.bracket_position, p.slot_id),
            )
            if len(finals) != len(placeholders):
                raise ValueError("qualification final/placeholder mapping is ambiguous")
            for source, placeholder in zip(finals, placeholders, strict=True):
                targets = [
                    (m, side)
                    for m in package.main_draw_matches
                    for side in ("top", "bottom")
                    if getattr(m, f"{side}_slot_id") == placeholder.slot_id
                ]
                if len(targets) != 1:
                    raise ValueError(
                        "qualification placeholder target side is ambiguous"
                    )
                target, side = targets[0]
                promotions.append(
                    FrozenQualifierPromotion(
                        qualifier_index=placeholder.qualifier_index,
                        source_match_id=source.match_id,
                        target_match_id=target.match_id,
                        target_side=side,
                        target_slot_id=placeholder.slot_id,
                    )
                )
        bye_ids = []
        for match in package.qualification_matches + package.main_draw_matches:
            if match.status != "bye_auto_advance_pending":
                continue
            known = [p for p in (match.top_player_id, match.bottom_player_id) if p]
            if len(known) != 1 or not match.winner_to_match_id:
                raise ValueError("persisted BYE advancement is ambiguous")
            match.winner_player_id = known[0]
            match.loser_player_id = None
            match.scoreline = "BYE"
            match.status = "completed"
            match.result_notes = "automatic BYE advance"
            match.result_fingerprint = fingerprint(
                {
                    "action": "authoritative_bye_advance.v1",
                    "event_id": package.event_id,
                    "match_id": match.match_id,
                    "winner_player_id": known[0],
                }
            )
            self.match_service._propagate_winner(package, completed=match)
            bye_ids.append(match.match_id)
        return package.model_copy(
            update={
                "frozen_qualifier_promotions": promotions,
                "frozen_bye_match_ids": bye_ids,
            }
        )

    def _package(self, week, *, required=True):
        """Legacy single-event discovery retained for reviewed compatibility."""
        packages = self._packages(week, required=required)
        if len(packages) > 1:
            raise ValueError(
                "multiple supported tournaments lack authoritative cross-event "
                "Simulation Slot chronology"
            )
        return packages[0] if packages else None

    @staticmethod
    def _decode_adopted_authority(payload_json):
        payload = json.loads(payload_json)
        version = payload.get("schema_version")

        if version == "adopted_tournament_authority.v6":
            items = []
            for item in payload["tournaments"]:
                event = CalendarEvent.model_validate(item["calendar_event"])
                evidence = _AdoptedTournamentEvidence(
                    event_id=item["event_id"],
                    calendar_event=event,
                    point_award_authority=FrozenPointAwardAuthority.model_validate(
                        item["point_award_authority"]
                    ),
                    draw_authority_fingerprint=item["draw_authority_fingerprint"],
                )
                if evidence.event_id != event.event_id:
                    raise ValueError(
                        "canonical adopted tournament event identity mismatch"
                    )
                items.append(evidence)
            return tuple(sorted(items, key=lambda item: item.event_id))

        if version == "adopted_tournament_authority.v5":
            return tuple(
                sorted(
                    (
                        _AdoptedTournamentEvidence(
                            event_id=package.event_id,
                            package=package,
                            point_award_authority=FrozenPointAwardAuthority.model_validate(
                                item["point_award_authority"]
                            ),
                            draw_authority_fingerprint=item.get(
                                "draw_authority_fingerprint"
                            ),
                        )
                        for item in payload["tournaments"]
                        for package in (
                            SeasonEventMatchPackage.model_validate(item["package"]),
                        )
                    ),
                    key=lambda item: item.event_id,
                )
            )

        if version in {
            "adopted_tournament_authority.v3",
            "adopted_tournament_authority.v4",
        }:
            return tuple(
                sorted(
                    (
                        _AdoptedTournamentEvidence(
                            event_id=package.event_id,
                            package=package,
                            point_award_authority=FrozenPointAwardAuthority.model_validate(
                                item["point_award_authority"]
                            ),
                        )
                        for item in payload["tournaments"]
                        for package in (
                            SeasonEventMatchPackage.model_validate(item["package"]),
                        )
                    ),
                    key=lambda item: item.event_id,
                )
            )

        if version == "adopted_tournament_authority.v2":
            package = SeasonEventMatchPackage.model_validate(payload["package"])
            return (
                _AdoptedTournamentEvidence(
                    event_id=package.event_id,
                    package=package,
                    point_award_authority=FrozenPointAwardAuthority.model_validate(
                        payload["point_award_authority"]
                    ),
                ),
            )

        package = SeasonEventMatchPackage.model_validate(payload)
        return (
            _AdoptedTournamentEvidence(
                event_id=package.event_id,
                package=package,
            ),
        )

    @staticmethod
    def _encode_adopted_authority(items):
        items = tuple(sorted(items, key=lambda item: item.event_id))
        canonical = all(
            item.package is None
            and item.calendar_event is not None
            and item.point_award_authority is not None
            and item.draw_authority_fingerprint is not None
            for item in items
        )
        if canonical:
            return json.dumps(
                {
                    "schema_version": "adopted_tournament_authority.v6",
                    "tournaments": [
                        {
                            "event_id": item.event_id,
                            "calendar_event": item.calendar_event.model_dump(
                                mode="json",
                                exclude_computed_fields=True,
                            ),
                            "point_award_authority": (
                                item.point_award_authority.model_dump(mode="json")
                            ),
                            "draw_authority_fingerprint": (
                                item.draw_authority_fingerprint
                            ),
                        }
                        for item in items
                    ],
                },
                sort_keys=True,
                separators=(",", ":"),
            )

        if any(item.package is None for item in items):
            raise ValueError(
                "adopted tournament week cannot mix canonical-only and legacy evidence"
            )
        return json.dumps(
            {
                "schema_version": "adopted_tournament_authority.v5",
                "tournaments": [
                    {
                        "package": item.package.model_dump(mode="json"),
                        "point_award_authority": (
                            item.point_award_authority.model_dump(mode="json")
                            if item.point_award_authority is not None
                            else None
                        ),
                        "draw_authority_fingerprint": (
                            item.draw_authority_fingerprint
                        ),
                    }
                    for item in items
                ],
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    def _freeze_calendar_event_snapshot(self, *, package, week):
        calendar = self.awards_service.calendar_service.get_calendar(
            season=package.season
        ).calendar
        if calendar is None:
            raise ValueError(
                "canonical tournament adoption requires Calendar authority"
            )
        matches = [
            event for event in calendar.events if event.event_id == package.event_id
        ]
        if len(matches) != 1:
            raise ValueError(
                "canonical tournament adoption requires unique Calendar Event"
            )
        event = matches[0]
        if event.season_week != week.week:
            raise ValueError(
                "canonical tournament Calendar Event belongs to a different week"
            )
        return CalendarEvent.model_validate(
            event.model_dump(mode="json", exclude_computed_fields=True)
        )

    def _authority_package(self, session, run_id, branch_id, week, *, adopt):
        row = session.get(
            AdoptedTournamentAuthorityModel, (run_id, branch_id, week.ordinal)
        )
        if row is not None:
            return self._replay_adopted_authority(
                session,
                run_id=run_id,
                branch_id=branch_id,
                week=week,
                row=row,
            )
        if not adopt:
            raise ValueError("frozen tournament authority is missing")

        packages = self._packages(
            week,
            session=session,
            run_id=run_id,
            branch_id=branch_id,
        )
        if (
            len(packages) > 1
            or len(
                self._topology_for_session(
                    session, run_id, branch_id, packages, week=week
                )
            )
            != 3
        ) and self._schedule(
            session, run_id, branch_id, week
        ) is None:
            raise ValueError(
                "tournaments lack authoritative explicit Simulation Slot chronology"
            )

        draw_store = TournamentDrawAuthorityStore(session)
        items = []
        for package in packages:
            point_authority = self.awards_service.freeze_point_award_authority(package)
            draw = draw_store.get(
                run_id=run_id,
                branch_id=branch_id,
                event_id=package.event_id,
            )
            if draw is None:
                items.append(
                    _AdoptedTournamentEvidence(
                        event_id=package.event_id,
                        package=package,
                        point_award_authority=point_authority,
                    )
                )
                continue

            event = self._freeze_calendar_event_snapshot(
                package=package,
                week=week,
            )
            rebuilt = self._bind_owned_draw_evidence(
                package=build_run_owned_match_package(
                    draw=draw,
                    event=event,
                    week=week,
                ),
                draw=draw,
                week=week,
            )
            if rebuilt != package:
                raise ValueError(
                    "canonical tournament package cannot replay from Draw + Calendar evidence"
                )
            items.append(
                _AdoptedTournamentEvidence(
                    event_id=package.event_id,
                    calendar_event=event,
                    point_award_authority=point_authority,
                    draw_authority_fingerprint=draw.fingerprint,
                )
            )
        items = tuple(items)

        authority_fp = self._tournament_authority_fingerprint(
            run_id, branch_id, week, items
        )
        session.add(
            AdoptedTournamentAuthorityModel(
                run_id=run_id,
                branch_id=branch_id,
                week_ordinal=week.ordinal,
                event_id=(
                    packages[0].event_id
                    if len(packages) == 1
                    else "__week_tournament_authority_bundle_v1__"
                ),
                authority_fingerprint=authority_fp,
                package_json=self._encode_adopted_authority(items),
            )
        )
        session.flush()
        return packages, authority_fp

    @staticmethod
    def _tournament_authority_fingerprint(run_id, branch_id, week, items):
        normalized = []
        for raw in items:
            if isinstance(raw, _AdoptedTournamentEvidence):
                normalized.append(raw)
                continue
            package, point_authority, draw_fp = raw
            normalized.append(
                _AdoptedTournamentEvidence(
                    event_id=package.event_id,
                    package=package,
                    point_award_authority=point_authority,
                    draw_authority_fingerprint=draw_fp,
                )
            )
        bodies = []
        for item in sorted(normalized, key=lambda item: item.event_id):
            if item.package is not None:
                payload = item.package.model_dump(mode="json")
                payload["metadata"].pop("persistence_path", None)
                body = {
                    "package": payload,
                    "point_award_authority": (
                        item.point_award_authority.model_dump(mode="json")
                        if item.point_award_authority
                        else None
                    ),
                }
                # Preserve historical v1-v4/v5 authority fingerprints exactly.
                if item.draw_authority_fingerprint is not None:
                    body["draw_authority_fingerprint"] = (
                        item.draw_authority_fingerprint
                    )
            else:
                if (
                    item.calendar_event is None
                    or item.point_award_authority is None
                    or item.draw_authority_fingerprint is None
                ):
                    raise ValueError(
                        "canonical adopted tournament evidence is incomplete"
                    )
                body = {
                    "event_id": item.event_id,
                    "calendar_event": item.calendar_event.model_dump(
                        mode="json",
                        exclude_computed_fields=True,
                    ),
                    "point_award_authority": (
                        item.point_award_authority.model_dump(mode="json")
                    ),
                    "draw_authority_fingerprint": (
                        item.draw_authority_fingerprint
                    ),
                }
            bodies.append(body)
        return fingerprint(
            {"scope": [run_id, branch_id, week.ordinal], "tournaments": bodies}
        )

    def _schedule(self, session, run_id, branch_id, week):
        row = session.get(
            WeekSimulationScheduleModel, (run_id, branch_id, week.ordinal)
        )
        if row is None:
            return None
        value = WeekSimulationSchedule.model_validate_json(row.payload_json)
        if value.fingerprint != row.schedule_fingerprint or (
            value.run_id,
            value.branch_id,
            value.week,
        ) != (run_id, branch_id, week):
            raise ValueError("adopted week schedule is corrupt")
        return value

    def inspect_schedule(self, *, run_id, branch_id):
        with self.factory() as session:
            week = self._current_week(session, run_id, branch_id)
            packages = self._packages(
                week,
                required=False,
                session=session,
                run_id=run_id,
                branch_id=branch_id,
            )
            schedule = self._schedule(session, run_id, branch_id, week)
            plans = self._topology_for_session(
                session, run_id, branch_id, packages, week=week
            ) if packages else {}
            requirement_position = self._position(
                session, run_id, branch_id, allow_missing_schedule=True
            )
            return {
                "run_id": run_id,
                "branch_id": branch_id,
                "week": week.model_dump(mode="json"),
                "required": len(packages) > 1 or len(plans) != 3,
                "event_ids": [p.event_id for p in packages],
                "group_ids": list(plans),
                "schedule": schedule.model_dump(mode="json") if schedule else None,
                "schedule_fingerprint": schedule.fingerprint if schedule else None,
                "expected_position_fingerprint": requirement_position.position_fingerprint,
            }

    def _build_topological_schedule_proposal(
        self,
        session,
        *,
        run_id: str,
        branch_id: str,
    ) -> tuple[WeekSimulationSchedule, str]:
        """Build one read-only dependency-safe proposal inside the caller scope."""
        week = self._current_week(session, run_id, branch_id)
        if self._schedule(session, run_id, branch_id, week) is not None:
            raise ValueError("week schedule is already adopted and immutable")

        current = self._position(
            session, run_id, branch_id, allow_missing_schedule=True
        )
        packages = self._packages(
            week,
            session=session,
            run_id=run_id,
            branch_id=branch_id,
        )
        plans = self._topology_for_session(
            session, run_id, branch_id, packages, week=week
        )
        if not plans:
            raise ValueError(
                "week has no authoritative tournament groups to schedule"
            )

        depth_cache: dict[str, int] = {}
        visiting: set[str] = set()

        def depth(group_id: str) -> int:
            if group_id in depth_cache:
                return depth_cache[group_id]
            if group_id in visiting:
                raise ValueError("week topology contains a feeder cycle")
            if group_id not in plans:
                raise ValueError("week topology references a missing feeder group")
            visiting.add(group_id)
            feeders = self._plan_feeders(plans[group_id])
            if any(feeder not in plans for feeder in feeders):
                raise ValueError(
                    "week topology references a feeder outside the authoritative graph"
                )
            value = (
                1
                if not feeders
                else 1 + max(depth(feeder) for feeder in feeders)
            )
            visiting.remove(group_id)
            depth_cache[group_id] = value
            return value

        for group_id in sorted(plans):
            depth(group_id)

        grouped: dict[int, list[str]] = {}
        for group_id, ordinal in depth_cache.items():
            grouped.setdefault(ordinal, []).append(group_id)

        slots: list[WeekSimulationScheduleSlot] = []
        for ordinal in sorted(grouped):
            group_ids = tuple(sorted(grouped[ordinal]))
            known_players: dict[str, str] = {}
            for group_id in group_ids:
                plan = plans[group_id]
                direct_ids = (
                    tuple(plan.direct_player_ids or ())
                    if plan.participant_sources is None
                    else tuple(
                        source.removeprefix("player:")
                        for source in plan.participant_sources
                        if source.startswith("player:")
                    )
                )
                for player_id in direct_ids:
                    prior_group = known_players.get(player_id)
                    if prior_group is not None:
                        raise ValueError(
                            "topological schedule proposal found one directly known "
                            "player in multiple independent groups of the same slot; "
                            "commitment/Week Tournament Lock authority must resolve "
                            f"the conflict before chronology ({player_id}: "
                            f"{prior_group}, {group_id})"
                        )
                    known_players[player_id] = group_id
            slots.append(
                WeekSimulationScheduleSlot(
                    ordinal=ordinal,
                    group_ids=group_ids,
                )
            )

        schedule = WeekSimulationSchedule(
            run_id=run_id,
            branch_id=branch_id,
            week=week,
            slots=tuple(slots),
        )
        self._validate_schedule(session, schedule, packages)
        position_fingerprint = fingerprint(
            {
                "position": current.position_fingerprint,
                "schedule": schedule.fingerprint,
            }
        )
        return schedule, position_fingerprint

    @staticmethod
    def _topological_schedule_proposal_payload(
        schedule: WeekSimulationSchedule,
        *,
        position_fingerprint: str,
    ) -> dict:
        return {
            "schedule": schedule.model_dump(mode="json"),
            "schedule_fingerprint": schedule.fingerprint,
            "position_fingerprint": position_fingerprint,
            "provenance": (
                "earliest_dependency_safe_topological_proposal_v1; "
                "not Match Day timing or Final Commitment authority"
            ),
            "persisted": False,
        }

    def propose_topological_schedule(self, *, run_id: str, branch_id: str):
        """Propose earliest dependency-safe Simulation Slots from canonical topology."""
        with self.factory() as session:
            self._require_writable_scope(session, run_id, branch_id)
            schedule, position_fingerprint = (
                self._build_topological_schedule_proposal(
                    session,
                    run_id=run_id,
                    branch_id=branch_id,
                )
            )
            return self._topological_schedule_proposal_payload(
                schedule,
                position_fingerprint=position_fingerprint,
            )

    def adopt_topological_schedule_proposal(
        self,
        *,
        run_id: str,
        branch_id: str,
        request_id: str,
        expected_week: RankingWeek,
        expected_schedule_fingerprint: str,
        expected_position_fingerprint: str,
    ):
        """Atomically rebuild and adopt the exact current topological proposal."""
        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            self._require_writable_scope(session, run_id, branch_id)
            current_week = self._current_week(session, run_id, branch_id)
            row = session.get(
                WeekSimulationScheduleModel,
                (run_id, branch_id, expected_week.ordinal),
            )
            if row is not None:
                stored = self._schedule(
                    session, run_id, branch_id, expected_week
                )
                assert stored is not None
                request_fp = fingerprint(
                    {
                        "request_id": request_id,
                        "schedule": stored.model_dump(mode="json"),
                    }
                )
                if (
                    row.request_id == request_id
                    and row.request_fingerprint == request_fp
                    and stored.fingerprint == expected_schedule_fingerprint
                ):
                    return {
                        "schedule": stored.model_dump(mode="json"),
                        "schedule_fingerprint": stored.fingerprint,
                        "adoption": "exact_retry",
                    }
                raise ValueError("week schedule is already adopted and immutable")

            if current_week != expected_week:
                raise ValueError("schedule week is stale")
            schedule, position_fingerprint = (
                self._build_topological_schedule_proposal(
                    session,
                    run_id=run_id,
                    branch_id=branch_id,
                )
            )
            if schedule.fingerprint != expected_schedule_fingerprint:
                raise ValueError("topological schedule proposal is stale")
            if position_fingerprint != expected_position_fingerprint:
                raise ValueError("simulation position is stale")

            request_fp = fingerprint(
                {
                    "request_id": request_id,
                    "schedule": schedule.model_dump(mode="json"),
                }
            )
            session.add(
                WeekSimulationScheduleModel(
                    run_id=run_id,
                    branch_id=branch_id,
                    week_ordinal=expected_week.ordinal,
                    request_id=request_id,
                    request_fingerprint=request_fp,
                    schedule_fingerprint=schedule.fingerprint,
                    payload_json=schedule.model_dump_json(),
                )
            )

        inspected = self.inspect_schedule(run_id=run_id, branch_id=branch_id)
        inspected["adoption"] = "adopted_topological_proposal"
        return inspected

    def adopt_schedule(
        self,
        schedule: WeekSimulationSchedule,
        *,
        request_id: str,
        expected_position_fingerprint: str,
    ):
        request_fp = fingerprint(
            {"request_id": request_id, "schedule": schedule.model_dump(mode="json")}
        )
        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            self._require_writable_scope(session, schedule.run_id, schedule.branch_id)
            current = self._position(
                session,
                schedule.run_id,
                schedule.branch_id,
                allow_missing_schedule=True,
            )
            row = session.get(
                WeekSimulationScheduleModel,
                (schedule.run_id, schedule.branch_id, schedule.week.ordinal),
            )
            if row:
                if (
                    row.request_id == request_id
                    and row.request_fingerprint == request_fp
                ):
                    return {
                        "schedule": schedule.model_dump(mode="json"),
                        "schedule_fingerprint": schedule.fingerprint,
                        "adoption": "exact_retry",
                    }
                raise ValueError("week schedule is already adopted and immutable")
            proposal_position = fingerprint(
                {
                    "position": current.position_fingerprint,
                    "schedule": schedule.fingerprint,
                }
            )
            if proposal_position != expected_position_fingerprint:
                raise ValueError("simulation position is stale")
            if current.current_week != schedule.week:
                raise ValueError("schedule week is stale")
            packages = self._packages(
                schedule.week,
                session=session,
                run_id=schedule.run_id,
                branch_id=schedule.branch_id,
            )
            self._validate_schedule(
                session,
                schedule,
                packages,
            )
            session.add(
                WeekSimulationScheduleModel(
                    run_id=schedule.run_id,
                    branch_id=schedule.branch_id,
                    week_ordinal=schedule.week.ordinal,
                    request_id=request_id,
                    request_fingerprint=request_fp,
                    schedule_fingerprint=schedule.fingerprint,
                    payload_json=schedule.model_dump_json(),
                )
            )
        return self.inspect_schedule(
            run_id=schedule.run_id, branch_id=schedule.branch_id
        )

    def preview_schedule(self, schedule: WeekSimulationSchedule):
        with self.factory() as session:
            self._require_writable_scope(session, schedule.run_id, schedule.branch_id)
            if self._schedule(
                session, schedule.run_id, schedule.branch_id, schedule.week
            ):
                raise ValueError("week schedule is already adopted and immutable")
            current = self._position(
                session,
                schedule.run_id,
                schedule.branch_id,
                allow_missing_schedule=True,
            )
            if current.current_week != schedule.week:
                raise ValueError("schedule week is stale")
            self._validate_schedule(
                session,
                schedule,
                self._packages(
                    schedule.week,
                    session=session,
                    run_id=schedule.run_id,
                    branch_id=schedule.branch_id,
                ),
            )
            return {
                "schedule": schedule.model_dump(mode="json"),
                "schedule_fingerprint": schedule.fingerprint,
                "position_fingerprint": fingerprint(
                    {
                        "position": current.position_fingerprint,
                        "schedule": schedule.fingerprint,
                    }
                ),
            }

    @staticmethod
    def _topology(packages):
        """Build the canonical executable DAG exclusively from persisted sources."""
        plans = {}
        for package in packages:
            if package.validation_errors:
                raise ValueError("persisted tournament topology has validation errors")
            matches = tuple(package.qualification_matches + package.main_draw_matches)
            by_id = {match.match_id: match for match in matches}
            if len(by_id) != len(matches):
                raise ValueError("persisted topology contains duplicate match identity")
            incoming = {match_id: [] for match_id in by_id}
            # Historical v1-v3 authority could omit feeder links for the reviewed
            # three-match compatibility shape. Keep that reader; new/general
            # topology never receives this inference.
            legacy_four = False
            if len(matches) == 3 and not any(m.winner_to_match_id for m in matches):
                _, ordered = validate_adopted_four_player_match_package(package)
                incoming[ordered[2].match_id] = [
                    ordered[0].match_id,
                    ordered[1].match_id,
                ]
                terminals = [ordered[2].match_id]
                legacy_four = True
            for match in matches:
                if match.event_id != package.event_id:
                    raise ValueError(
                        "tournaments lack authoritative cross-event identity: "
                        "persisted topology contains a foreign event match"
                    )
                if match.winner_to_match_id:
                    if match.winner_to_match_id not in by_id:
                        raise ValueError(
                            "persisted topology feeder target does not exist"
                        )
                    incoming[match.winner_to_match_id].append(match.match_id)
            promotion_by_target = {
                (item.target_match_id, item.target_side): item.source_match_id
                for item in package.frozen_qualifier_promotions
            }
            for item in package.frozen_qualifier_promotions:
                if (
                    item.source_match_id not in by_id
                    or item.target_match_id not in by_id
                ):
                    raise ValueError(
                        "frozen qualifier promotion references a missing match"
                    )
                incoming[item.target_match_id].append(item.source_match_id)
            visiting, visited = set(), set()

            def validate_acyclic(node):
                if node in visiting:
                    raise ValueError("persisted topology contains a feeder cycle")
                if node in visited:
                    return
                visiting.add(node)
                target = by_id[node].winner_to_match_id
                if target:
                    validate_acyclic(target)
                visiting.remove(node)
                visited.add(node)

            for node in by_id:
                validate_acyclic(node)
            bye_winners = {}
            for match in matches:
                if match.match_id in package.frozen_bye_match_ids:
                    known = [
                        p for p in (match.top_player_id, match.bottom_player_id) if p
                    ]
                    winner = match.winner_player_id or (
                        known[0] if len(known) == 1 else None
                    )
                    if winner is None or not match.winner_to_match_id:
                        raise ValueError("persisted BYE advancement is ambiguous")
                    bye_winners[match.match_id] = winner

            def node_ref(match_id):
                parts = match_id.split(":")
                rounds = [p for p in parts if p.startswith("R") and p[1:].isdigit()]
                numbers = [p for p in parts if p.startswith("M") and p[1:].isdigit()]
                return (
                    f"{rounds[0]}-N{numbers[0][1:]}" if rounds and numbers else match_id
                )

            for match in matches:
                if match.match_id in bye_winners:
                    continue
                sources = []
                for side_index, side in enumerate(("top", "bottom")):
                    promoted = promotion_by_target.get((match.match_id, side))
                    candidates = [
                        feeder
                        for feeder in incoming[match.match_id]
                        if getattr(match, f"{side}_source") == node_ref(feeder)
                        or getattr(match, f"{side}_slot_id") == feeder
                    ]
                    feeder = promoted or (
                        candidates[0] if len(candidates) == 1 else None
                    )
                    if (
                        feeder is None
                        and legacy_four
                        and len(incoming[match.match_id]) == 2
                    ):
                        feeder = incoming[match.match_id][side_index]
                    if feeder in bye_winners:
                        sources.append(f"player:{bye_winners[feeder]}")
                    elif feeder:
                        sources.append(f"winner:{feeder}")
                    else:
                        player_id = getattr(match, f"{side}_player_id")
                        if not player_id:
                            raise ValueError(
                                "persisted topology has an unresolved participant source"
                            )
                        sources.append(f"player:{player_id}")
                plan = SimulationMatchEventPlan(
                    group_id=match.match_id,
                    event_id=package.event_id,
                    match_id=match.match_id,
                    participant_sources=tuple(sources),
                )
                if match.match_id in plans:
                    raise ValueError("week topology contains duplicate group identity")
                plans[match.match_id] = plan

            # Acyclicity and reachability are validated independently of authored
            # round names/numbers. Every node must drain into the sole terminal.
            terminals = (
                terminals
                if legacy_four
                else [
                    m.match_id
                    for m in package.main_draw_matches
                    if not m.winner_to_match_id
                ]
            )
            if len(terminals) != 1:
                raise ValueError(
                    "persisted topology must identify exactly one terminal match"
                )
        return plans

    def _topology_for_session(
        self, session, run_id, branch_id, packages, *, week
    ):
        """Prefer the Draw source frozen for this tournament authority generation."""
        if not packages:
            return {}
        canonical = []
        for package in packages:
            draw = self._canonical_draw_binding(
                session,
                run_id=run_id,
                branch_id=branch_id,
                week=week,
                event_id=package.event_id,
            )
            canonical.append((package, draw))
        if all(draw is None for _, draw in canonical):
            return self._topology(packages)
        if any(draw is None for _, draw in canonical):
            raise ValueError(
                "week mixes canonical Draw authority with legacy-only tournament topology"
            )
        plans = {}
        for package, draw in canonical:
            projection = project_canonical_draw_to_match_topology(
                draw=draw,
                package=package,
            )
            for plan in projection.plans:
                if plan.group_id in plans:
                    raise ValueError("week topology contains duplicate group identity")
                plans[plan.group_id] = plan
        return plans

    def _validate_schedule(self, session, schedule, packages):
        plans = self._topology_for_session(
            session,
            schedule.run_id,
            schedule.branch_id,
            packages,
            week=schedule.week,
        )
        authored_sequence = tuple(g for slot in schedule.slots for g in slot.group_ids)
        if len(authored_sequence) != len(set(authored_sequence)) or set(
            authored_sequence
        ) != set(plans):
            raise ValueError("schedule must cover every supported group exactly once")
        ordinal = {g: slot.ordinal for slot in schedule.slots for g in slot.group_ids}
        for group_id, plan in plans.items():
            for feeder in self._plan_feeders(plan):
                if ordinal[feeder] >= ordinal[group_id]:
                    raise ValueError(
                        "dependent groups require a strictly later slot than feeders"
                    )

    @staticmethod
    def _plan_feeders(plan):
        if plan.participant_sources:
            return tuple(
                source.removeprefix("winner:")
                for source in plan.participant_sources
                if source.startswith("winner:")
            )
        return tuple(plan.feeder_group_ids or ())

    def _position(self, session, run_id, branch_id, *, allow_missing_schedule=False):
        week = self._current_week(session, run_id, branch_id)
        frozen = session.get(
            AdoptedTournamentAuthorityModel, (run_id, branch_id, week.ordinal)
        )
        packages = (
            self._authority_package(session, run_id, branch_id, week, adopt=False)[0]
            if frozen
            else self._packages(
                week,
                required=False,
                session=session,
                run_id=run_id,
                branch_id=branch_id,
            )
        )
        schedule = self._schedule(session, run_id, branch_id, week)
        if (
            schedule is None
            and packages
            and (
                len(packages) > 1
                or len(
                    self._topology_for_session(
                        session, run_id, branch_id, packages, week=week
                    )
                )
                != 3
            )
            and not allow_missing_schedule
        ):
            raise ValueError(
                "tournaments lack authoritative cross-event or general-draw "
                "Simulation Slot chronology"
            )
        slots = session.scalars(
            select(SimulationSlotModel)
            .where(
                SimulationSlotModel.run_id == run_id,
                SimulationSlotModel.branch_id == branch_id,
                SimulationSlotModel.week_ordinal == week.ordinal,
            )
            .order_by(SimulationSlotModel.slot_ordinal)
        ).all()
        groups = session.scalars(
            select(SimulationEventGroupModel).where(
                SimulationEventGroupModel.run_id == run_id,
                SimulationEventGroupModel.branch_id == branch_id,
                SimulationEventGroupModel.week_ordinal == week.ordinal,
            )
        ).all()
        done = {g.group_id for g in groups}
        plans = (
            self._topology_for_session(
                session, run_id, branch_id, packages, week=week
            )
            if packages
            else {}
        )
        current = next((s for s in slots if s.status != "complete"), None)
        authored_slots = schedule.slots if schedule else ()
        if not authored_slots and len(packages) == 1 and len(plans) == 3:
            matches = sorted(
                packages[0].main_draw_matches,
                key=lambda m: (m.round_number, m.bracket_position),
            )
            authored_slots = (
                type(
                    "S",
                    (),
                    {"ordinal": 1, "group_ids": tuple(m.match_id for m in matches[:2])},
                )(),
                type("S", (), {"ordinal": 2, "group_ids": (matches[2].match_id,)})(),
            )
        next_spec = next(
            (x for x in authored_slots if any(g not in done for g in x.group_ids)), None
        )
        current_ids = tuple(
            current
            and AuthoritativeSlotMatchExecutor._load_plan(current).group_ids
            or (next_spec.group_ids if next_spec else ())
        )
        unresolved = tuple(g for g in current_ids if g not in done)
        eligible_groups = tuple(
            g for g in unresolved if set(self._plan_feeders(plans[g])) <= done
        )
        blocked_groups = tuple(
            g for g in plans if g not in done and g not in eligible_groups
        )
        owned_store = OwnedTournamentRankingSourceStore(session)
        owned = {
            p.event_id: owned_store.get(
                run_id=run_id, branch_id=branch_id, edition_id=p.event_id
            )
            for p in packages
        }
        executor = AuthoritativeSlotMatchExecutor(session)
        terminal = (
            executor.terminal_checkpoint(run_id=run_id, branch_id=branch_id, week=week)
            if slots and all(s.status == "complete" for s in slots)
            else None
        )
        blockers = []
        if schedule is None and (len(packages) > 1 or len(plans) != 3):
            blockers.append("week_schedule_missing")
        if set(done) != set(plans):
            blockers.append("pending_authoritative_groups")
        if any(v is None for v in owned.values()):
            blockers.append("tournament_source_missing")
        if terminal is None:
            blockers.append("terminal_sporting_checkpoint_missing")
        lifecycle = get_lifecycle(
            session, run_id=run_id, branch_id=branch_id, week=week
        )
        if lifecycle is None:
            blockers.append("lifecycle_roster_missing")
        if not blockers:
            try:
                preflight_completed_context_from_authoritative_matches(
                    session,
                    run_id=run_id,
                    branch_id=branch_id,
                    completed_week=week,
                    player_ids=tuple(p.player_id for p in lifecycle.players),
                )
                if any(x.binding.completed_week != week for x in owned.values()):
                    raise ValueError()
            except ValueError:
                blockers.append("week_transition_sporting_preflight_failed")
        if not (week.season_index == 49 and week.week == 61):
            blockers.extend(
                x
                for x in preview_persisted_week_transition(
                    session,
                    self.awards_service,
                    run_id=run_id,
                    branch_id=branch_id,
                    completed_week=week,
                )
                if x not in blockers
            )
        branch = session.get(RunBranchModel, branch_id)
        draft = session.scalar(
            select(BranchWorkingDraftModel).where(
                BranchWorkingDraftModel.branch_id == branch_id
            )
        )
        sporting = get_sporting(session, run_id=run_id, branch_id=branch_id, week=week)
        transition_authority = session.get(
            RankingTransitionAuthorityModel, (run_id, branch_id, week.ordinal + 1)
        )
        world = session.get(AuthoritativeWorldStateModel, (run_id, branch_id))
        body = {
            "scope": [run_id, branch_id, week.ordinal],
            "schedule": schedule.fingerprint if schedule else None,
            "proposed_schedule_requirement": [p.event_id for p in packages],
            "slots": [
                (s.slot_id, s.status, s.plan_fingerprint, s.terminal_checkpoint_json)
                for s in slots
            ],
            "groups": [
                (g.group_id, g.command_fingerprint, g.result_fingerprint)
                for g in sorted(groups, key=lambda x: x.group_id)
            ],
            "owned": sorted(
                (k, v.fingerprint if v else None) for k, v in owned.items()
            ),
            "tournament_authority": frozen.authority_fingerprint
            if frozen
            else (
                self._tournament_authority_fingerprint(
                    run_id,
                    branch_id,
                    week,
                    tuple(
                        (
                            p,
                            self.awards_service.freeze_point_award_authority(p),
                            (
                                draw.fingerprint
                                if (
                                    draw := TournamentDrawAuthorityStore(session).get(
                                        run_id=run_id,
                                        branch_id=branch_id,
                                        event_id=p.event_id,
                                    )
                                )
                                is not None
                                else None
                            ),
                        )
                        for p in packages
                    ),
                )
                if packages
                else None
            ),
            "sporting": sporting.fingerprint if sporting else None,
            "lifecycle": lifecycle.fingerprint if lifecycle else None,
            "branch_head": branch.saved_head_revision_id if branch else None,
            "draft": [draft.base_revision_id, draft.status, draft.draft_version]
            if draft
            else None,
            "transition_authority": (
                transition_authority.fingerprint if transition_authority else None
            ),
            "world": (
                [world.current_ordinal, world.ranking_fingerprint] if world else None
            ),
            "terminal": terminal.fingerprint if terminal else None,
        }
        ready = not blockers
        return AuthoritativeSimulationPosition(
            run_id=run_id,
            branch_id=branch_id,
            current_week=week,
            current_slot_id=current.slot_id
            if current
            else (
                (
                    f"week-{week.ordinal}:slot:{next_spec.ordinal}"
                    if schedule
                    else f"{packages[0].event_id}:slot:{next_spec.ordinal}"
                )
                if next_spec
                else None
            ),
            slot_ordinal=current.slot_ordinal
            if current
            else (next_spec.ordinal if next_spec else None),
            unresolved_group_ids=unresolved,
            eligible_match_ids=tuple(plans[g].match_id for g in eligible_groups),
            blocked_match_ids=tuple(plans[g].match_id for g in blocked_groups),
            current_slot_complete=not unresolved,
            supported_tournament_complete=bool(packages) and all(owned.values()),
            week_ready_for_transition=ready,
            transition_blockers=tuple(blockers),
            terminal_sporting_fingerprint=terminal.fingerprint if terminal else None,
            position_fingerprint=fingerprint(body),
        )

    def _ensure_current_slot(self, session, command, packages):
        pos = self._position(session, command.run_id, command.branch_id)
        if any(
            s.status != "complete"
            for s in session.scalars(
                select(SimulationSlotModel).where(
                    SimulationSlotModel.run_id == command.run_id,
                    SimulationSlotModel.branch_id == command.branch_id,
                    SimulationSlotModel.week_ordinal == command.expected_week.ordinal,
                )
            ).all()
        ):
            return
        schedule = self._schedule(
            session, command.run_id, command.branch_id, command.expected_week
        )
        plans = self._topology_for_session(
            session,
            command.run_id,
            command.branch_id,
            packages,
            week=command.expected_week,
        )
        if schedule:
            spec = next(x for x in schedule.slots if x.ordinal == pos.slot_ordinal)
        else:
            ids = tuple(plans)
            spec = type(
                "S",
                (),
                {
                    "ordinal": pos.slot_ordinal,
                    "group_ids": ids[:2] if pos.slot_ordinal == 1 else ids[2:],
                },
            )()
        selected = tuple(plans[g] for g in spec.group_ids)
        authority_fp = self._authority_package(
            session,
            command.run_id,
            command.branch_id,
            command.expected_week,
            adopt=False,
        )[1]
        AuthoritativeSlotMatchExecutor(session).create_slot(
            run_id=command.run_id,
            branch_id=command.branch_id,
            week=command.expected_week,
            slot_id=pos.current_slot_id,
            ordinal=spec.ordinal,
            group_ids=spec.group_ids,
            match_events=selected,
            dependency_ids=tuple(f for p in selected for f in self._plan_feeders(p)),
            provenance=f"adopted-authority:{authority_fp};week-schedule:{schedule.fingerprint if schedule else 'single-event-compat'}",
        )

    def _eligible_groups(self, session, position, packages):
        slot = session.get(
            SimulationSlotModel,
            (
                position.run_id,
                position.branch_id,
                position.current_week.ordinal,
                position.current_slot_id,
            ),
        )
        plan = AuthoritativeSlotMatchExecutor._load_plan(slot)
        return tuple(
            e.group_id
            for e in plan.match_events
            if e.match_id in position.eligible_match_ids
        )

    def _execute_group(self, session, command, packages, group_id):
        pos = self._position(session, command.run_id, command.branch_id)
        slot = session.get(
            SimulationSlotModel,
            (
                command.run_id,
                command.branch_id,
                command.expected_week.ordinal,
                pos.current_slot_id,
            ),
        )
        plan = AuthoritativeSlotMatchExecutor._load_plan(slot)
        event = next(e for e in plan.match_events if e.group_id == group_id)
        package = next(p for p in packages if p.event_id == event.event_id)
        if event.participant_sources:
            players = tuple(
                source.removeprefix("player:")
                if source.startswith("player:")
                else AuthoritativeSlotMatchExecutor._load_group(
                    session.scalar(
                        select(SimulationEventGroupModel).where(
                            SimulationEventGroupModel.run_id == command.run_id,
                            SimulationEventGroupModel.branch_id == command.branch_id,
                            SimulationEventGroupModel.week_ordinal
                            == command.expected_week.ordinal,
                            SimulationEventGroupModel.group_id
                            == source.removeprefix("winner:"),
                        )
                    )
                ).result.winner_player_id
                for source in event.participant_sources
            )
        elif event.direct_player_ids:
            players = event.direct_player_ids
        else:
            players = tuple(
                AuthoritativeSlotMatchExecutor._load_group(
                    session.scalar(
                        select(SimulationEventGroupModel).where(
                            SimulationEventGroupModel.run_id == command.run_id,
                            SimulationEventGroupModel.branch_id == command.branch_id,
                            SimulationEventGroupModel.week_ordinal
                            == command.expected_week.ordinal,
                            SimulationEventGroupModel.group_id == f,
                        )
                    )
                ).result.winner_player_id
                for f in event.feeder_group_ids
            )
        authority_fp = self._authority_package(
            session,
            command.run_id,
            command.branch_id,
            command.expected_week,
            adopt=False,
        )[1]
        seed = int(
            hashlib.sha256(
                f"{command.run_id}|{command.branch_id}|{command.expected_week.ordinal}|{authority_fp}|{group_id}".encode()
            ).hexdigest()[:15],
            16,
        )
        AuthoritativeSlotMatchExecutor(session).execute_match_group(
            run_id=command.run_id,
            branch_id=command.branch_id,
            week=command.expected_week,
            slot_id=slot.slot_id,
            group_id=group_id,
            event_id=package.event_id,
            match_id=event.match_id,
            player_a_id=players[0],
            player_b_id=players[1],
            seed=seed,
            expected_slot_start_fingerprint=plan.slot_start_fingerprint,
        )

    def _advance_or_close(self, session, command, packages, *, fault_at=None):
        # Tournament close is distinct from Week/Season Transition. Week 61 must
        # still freeze completed tournament sources before the season boundary can
        # consume them; _position() separately exposes season_transition_required.
        executor = AuthoritativeSlotMatchExecutor(session)
        loaded = {
            g.group_id: executor._load_group(g)
            for g in session.scalars(
                select(SimulationEventGroupModel).where(
                    SimulationEventGroupModel.run_id == command.run_id,
                    SimulationEventGroupModel.branch_id == command.branch_id,
                    SimulationEventGroupModel.week_ordinal
                    == command.expected_week.ordinal,
                )
            ).all()
        }
        items = self._decode_adopted_authority(
            session.get(
                AdoptedTournamentAuthorityModel,
                (command.run_id, command.branch_id, command.expected_week.ordinal),
            ).package_json
        )
        evidence_by_event = {item.event_id: item for item in items}
        if set(evidence_by_event) != {package.event_id for package in packages}:
            raise ValueError(
                "frozen tournament authority package universe changed"
            )
        for package in packages:
            evidence = evidence_by_event[package.event_id]
            point_authority = evidence.point_award_authority
            draw_fp = evidence.draw_authority_fingerprint
            matches = tuple(
                m
                for m in package.qualification_matches + package.main_draw_matches
                if m.match_id not in package.frozen_bye_match_ids
            )
            if not all(m.match_id in loaded for m in matches):
                continue
            if draw_fp is not None:
                draw = TournamentDrawAuthorityStore(session).get(
                    run_id=command.run_id,
                    branch_id=command.branch_id,
                    event_id=package.event_id,
                )
                if draw is None or draw.fingerprint != draw_fp:
                    raise ValueError(
                        "frozen tournament canonical Draw binding changed"
                    )
                projection = project_canonical_draw_to_match_topology(
                    draw=draw,
                    package=package,
                )
                terminal_match_id = projection.terminal_group_id
            else:
                terminals = tuple(
                    m
                    for m in package.main_draw_matches
                    if m.match_id not in package.frozen_bye_match_ids
                    and not m.winner_to_match_id
                )
                if len(matches) == 3 and len(terminals) == 3:
                    _, ordered = validate_adopted_four_player_match_package(package)
                    terminals = (ordered[2],)
                if len(terminals) != 1:
                    raise ValueError(
                        "frozen tournament topology has ambiguous terminal"
                    )
                terminal_match_id = terminals[0].match_id
            auth = AuthoritativeTournamentResult(
                event_id=package.event_id,
                groups=tuple(loaded[m.match_id] for m in matches),
                terminal_group_ids=(terminal_match_id,),
                champion_player_id=loaded[
                    terminal_match_id
                ].result.winner_player_id,
                match_result_fingerprints=tuple(
                    loaded[m.match_id].result_fingerprint for m in matches
                ),
            )
            if fault_at == "after_final_before_source":
                raise RuntimeError(
                    "fault after tournament final before ranking source persistence"
                )
            store = OwnedTournamentRankingSourceStore(session)
            existing = store.get(
                run_id=command.run_id,
                branch_id=command.branch_id,
                edition_id=package.event_id,
            )
            if existing:
                self._validate_existing_owned_source(existing, command, package, auth)
                continue
            canonical_result = None
            canonical_awards = None
            canonical_prize_awards = None
            result = None
            awards = None
            if draw_fp is not None:
                (
                    _,
                    canonical_result,
                    canonical_awards,
                    canonical_prize_awards,
                ) = build_run_owned_tournament_authorities(
                    package=package,
                    authoritative=auth,
                    draw=draw,
                    run_id=command.run_id,
                    branch_id=command.branch_id,
                    week=command.expected_week,
                    calendar_event=evidence.calendar_event,
                    award_seed=self._stable_seed(package, "awards"),
                    frozen_point_authority=point_authority,
                )
            else:
                _, result, awards = build_authoritative_tournament_ranking_packages(
                    self.awards_service,
                    package=package,
                    authoritative=auth,
                    result_seed=self._stable_seed(package, "result"),
                    award_seed=self._stable_seed(package, "awards"),
                    frozen_point_authority=point_authority,
                )
            first_publication_week, closing_eligibility_ordinal = (
                self._ranking_source_boundary(command.expected_week)
            )
            binding = TournamentRankingBinding(
                run_id=command.run_id,
                branch_id=command.branch_id,
                edition_id=package.event_id,
                event_id=package.event_id,
                completed_week=command.expected_week,
                first_publication_week=first_publication_week,
                closing_eligibility_ordinal=closing_eligibility_ordinal,
                validity_weeks=61,
                ranking_status="ranked",
                expected_result_fingerprint=(
                    canonical_result.fingerprint
                    if canonical_result is not None
                    else result.metadata.build_fingerprint
                ),
                expected_award_fingerprint=(
                    canonical_awards.fingerprint
                    if canonical_awards is not None
                    else awards.metadata.build_fingerprint
                ),
            )
            if canonical_result is not None and canonical_awards is not None:
                if binding.closing_only:
                    prepare_final_season_closing_ranking_results(
                        binding,
                        canonical_result,
                        canonical_awards,
                    )
                    source = OwnedTournamentRankingSource(
                        schema_version="owned_tournament_ranking_source.v6",
                        binding=binding,
                        canonical_result=canonical_result,
                        canonical_awards=canonical_awards,
                        canonical_prize_awards=canonical_prize_awards,
                        adopted_by_command_id=command.command_id,
                        provenance_kind=(
                            "canonical_run_owned_tournament_authorities_and_prize_money_final_closing"
                            if canonical_prize_awards is not None
                            else "canonical_run_owned_tournament_authorities_final_closing"
                        ),
                    )
                else:
                    prepare_canonical_tournament_ranking_sources(
                        binding,
                        canonical_result,
                        canonical_awards,
                    )
                    if canonical_prize_awards is not None:
                        source = OwnedTournamentRankingSource(
                            schema_version="owned_tournament_ranking_source.v5",
                            binding=binding,
                            canonical_result=canonical_result,
                            canonical_awards=canonical_awards,
                            canonical_prize_awards=canonical_prize_awards,
                            adopted_by_command_id=command.command_id,
                            provenance_kind=(
                                "canonical_run_owned_tournament_authorities_and_prize_money"
                            ),
                        )
                    else:
                        # Historical adopted authorities before Calendar Event snapshot
                        # freezing cannot reconstruct prize configuration safely.
                        source = OwnedTournamentRankingSource(
                            schema_version="owned_tournament_ranking_source.v4",
                            binding=binding,
                            canonical_result=canonical_result,
                            canonical_awards=canonical_awards,
                            adopted_by_command_id=command.command_id,
                            provenance_kind="canonical_run_owned_tournament_authorities",
                        )
            else:
                if result is None or awards is None:
                    raise ValueError("Legacy tournament close produced no packages")
                if binding.closing_only:
                    raise ValueError(
                        "Final Season Closing Ranking requires canonical tournament source"
                    )
                prepare_tournament_ranking_sources(binding, result, awards)
                source = OwnedTournamentRankingSource(
                    schema_version="owned_tournament_ranking_source.v1",
                    binding=binding,
                    result=result,
                    awards=awards,
                    adopted_by_command_id=command.command_id,
                    provenance_kind="explicit_legacy_tournament_adoption",
                )
            store.append(source)

    @staticmethod
    def _ranking_source_boundary(
        completed_week: RankingWeek,
    ) -> tuple[RankingWeek | None, int | None]:
        """Return Official publication or final Closing-only eligibility boundary."""

        if completed_week.week < 61:
            return (
                RankingWeek(
                    season_index=completed_week.season_index,
                    week=completed_week.week + 1,
                ),
                None,
            )
        if completed_week.season_index < 49:
            return (
                RankingWeek(
                    season_index=completed_week.season_index + 1,
                    week=1,
                ),
                None,
            )
        return None, completed_week.ordinal + 1

    @staticmethod
    def _validate_existing_owned_source(existing, command, package, authoritative):
        binding = existing.binding
        if (
            binding.run_id,
            binding.branch_id,
            binding.edition_id,
            binding.event_id,
            binding.completed_week,
        ) != (
            command.run_id,
            command.branch_id,
            package.event_id,
            package.event_id,
            command.expected_week,
        ):
            raise ValueError("Conflicting owned tournament source")
        expected = {
            g.authoritative_input.match_id: g.result_fingerprint
            for g in authoritative.groups
        }
        if existing.canonical_result is not None:
            stored_results = {
                r.match_id: r.result_fingerprint
                for r in existing.canonical_result.matches
            }
        else:
            if existing.result is None:
                raise ValueError("Historical owned tournament source is incomplete")
            stored_results = {
                r.match_id: r.result_fingerprint
                for r in existing.result.match_result_refs
            }
        if stored_results != expected:
            raise ValueError("Conflicting owned tournament source")
        if existing.schema_version == "owned_tournament_ranking_source.v6":
            if existing.canonical_result is None or existing.canonical_awards is None:
                raise ValueError("Final Closing tournament source is incomplete")
            prepare_final_season_closing_ranking_results(
                existing.binding,
                existing.canonical_result,
                existing.canonical_awards,
            )
        elif existing.schema_version in {
            "owned_tournament_ranking_source.v3",
            "owned_tournament_ranking_source.v4",
            "owned_tournament_ranking_source.v5",
        }:
            if existing.canonical_result is None or existing.canonical_awards is None:
                raise ValueError("Canonical owned tournament source is incomplete")
            prepare_canonical_tournament_ranking_sources(
                existing.binding,
                existing.canonical_result,
                existing.canonical_awards,
            )
        else:
            if existing.result is None or existing.awards is None:
                raise ValueError("Historical owned tournament source is incomplete")
            prepare_tournament_ranking_sources(
                existing.binding, existing.result, existing.awards
            )

    @staticmethod
    def _stable_seed(package, suffix):
        return int(
            hashlib.sha256(
                f"{package.metadata.build_fingerprint}|{suffix}".encode()
            ).hexdigest()[:15],
            16,
        )
