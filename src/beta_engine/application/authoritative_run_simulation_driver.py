"""Run/Branch-owned orchestration over the authoritative Simulation Slot ledger.

This intentionally supports only the persisted four-player Main Draw bridge.  It
does not mutate, or use as execution state, the legacy match/result/award files.
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
    AuthoritativeFourPlayerTournamentResult,
    AuthoritativeSlotMatchExecutor,
    build_authoritative_tournament_ranking_packages,
    validate_adopted_four_player_match_package,
)
from beta_engine.application.ranking_tournament_ingestion import (
    TournamentRankingBinding,
    prepare_tournament_ranking_sources,
)
from beta_engine.application.season_match_service import (
    SeasonEventMatchPackage,
    SeasonMatchService,
)
from beta_engine.application.season_point_awards_service import (
    FrozenPointAwardAuthority,
    SeasonPointAwardsService,
)
from beta_engine.domain.rankings.official import FrozenInput, RankingWeek
from beta_engine.domain.rankings.tournament_source import OwnedTournamentRankingSource
from beta_engine.domain.simulation_slots import SimulationMatchEventPlan, fingerprint
from beta_engine.infrastructure.db.models import (
    AuthoritativeSimulationCommandModel,
    AuthoritativeWorldStateModel,
    AdoptedTournamentAuthorityModel,
    BranchWorkingDraftModel,
    PlayerSportingWeekStateModel,
    RunBranchModel,
    RunContainerModel,
    RankingTransitionAuthorityModel,
    SimulationEventGroupModel,
    SimulationSlotModel,
)
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
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

    def simulate_next_match(self, command: AuthoritativeSimulationCommand):
        return self._mutate(command, mode="match")

    def simulate_next_slot(
        self, command: AuthoritativeSimulationCommand, *, fault_at: str | None = None
    ):
        return self._mutate(command, mode="slot", fault_at=fault_at)

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
                package, authority_fp = self._authority_package(
                    session,
                    command.run_id,
                    command.branch_id,
                    before.current_week,
                    adopt=True,
                )
                self._ensure_current_slot(session, command, package)
                position = self._position(session, command.run_id, command.branch_id)
                targets = self._targets(session, command, mode, position, package)
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
                package = self._pending_package(session, command, request_fp)
                current = self._position(session, command.run_id, command.branch_id)
                if group_id in current.unresolved_group_ids:
                    self._execute_group(session, command, package, group_id)
            if fault_at == "after_first_group" and index == 0:
                raise RuntimeError("fault after first committed group")

        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            self._require_writable_scope(session, command.run_id, command.branch_id)
            package = self._pending_package(session, command, request_fp)
            self._advance_or_close(session, command, package, fault_at=fault_at)
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
        package, authority_fp = self._authority_package(
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
        return package

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

    def _package(self, week, *, required=True):
        season = f"{2000 + week.season_index}/{2001 + week.season_index}"
        candidates = [
            p
            for p in self.match_service._load_registry().matches_by_event_id.values()
            if p.season == season and p.season_week == week.week
        ]
        if not candidates and not required:
            return None
        if not candidates:
            raise ValueError("supported tournament authority is missing")
        if len(candidates) > 1:
            raise ValueError(
                "multiple supported tournaments lack authoritative cross-event "
                "Simulation Slot chronology"
            )
        package = candidates[0]
        validate_adopted_four_player_match_package(package)
        return package

    @staticmethod
    def _decode_adopted_authority(payload_json):
        payload = json.loads(payload_json)
        if payload.get("schema_version") == "adopted_tournament_authority.v2":
            return (
                SeasonEventMatchPackage.model_validate(payload["package"]),
                FrozenPointAwardAuthority.model_validate(
                    payload["point_award_authority"]
                ),
            )
        return SeasonEventMatchPackage.model_validate(payload), None

    @staticmethod
    def _encode_adopted_authority(package, point_authority):
        return json.dumps(
            {
                "schema_version": "adopted_tournament_authority.v2",
                "package": package.model_dump(mode="json"),
                "point_award_authority": point_authority.model_dump(mode="json"),
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    def _authority_package(self, session, run_id, branch_id, week, *, adopt):
        row = session.get(
            AdoptedTournamentAuthorityModel, (run_id, branch_id, week.ordinal)
        )
        if row is not None:
            package, point_authority = self._decode_adopted_authority(row.package_json)
            authority_fp = self._tournament_authority_fingerprint(
                run_id, branch_id, week, package, point_authority
            )
            if (
                authority_fp != row.authority_fingerprint
                or package.event_id != row.event_id
            ):
                raise ValueError("frozen tournament authority is corrupt")
            return package, authority_fp
        if not adopt:
            raise ValueError("frozen tournament authority is missing")
        package = self._package(week)
        if package is None:
            raise ValueError("supported tournament authority is missing")
        point_authority = self.awards_service.freeze_point_award_authority(package)
        authority_fp = self._tournament_authority_fingerprint(
            run_id, branch_id, week, package, point_authority
        )
        session.add(
            AdoptedTournamentAuthorityModel(
                run_id=run_id,
                branch_id=branch_id,
                week_ordinal=week.ordinal,
                event_id=package.event_id,
                authority_fingerprint=authority_fp,
                package_json=self._encode_adopted_authority(package, point_authority),
            )
        )
        session.flush()
        return package, authority_fp

    def _point_award_authority(self, session, run_id, branch_id, week):
        row = session.get(
            AdoptedTournamentAuthorityModel, (run_id, branch_id, week.ordinal)
        )
        if row is None:
            raise ValueError("frozen tournament authority is missing")
        _, point_authority = self._decode_adopted_authority(row.package_json)
        return point_authority

    @staticmethod
    def _tournament_authority_fingerprint(
        run_id, branch_id, week, package, point_authority=None
    ):
        payload = package.model_dump(mode="json")
        payload["metadata"].pop("persistence_path", None)
        body = {"scope": [run_id, branch_id, week.ordinal], "package": payload}
        if point_authority is not None:
            body["point_award_authority"] = point_authority.model_dump(mode="json")
        return fingerprint(body)

    def _position(self, session, run_id, branch_id):
        week = self._current_week(session, run_id, branch_id)
        frozen = session.get(
            AdoptedTournamentAuthorityModel, (run_id, branch_id, week.ordinal)
        )
        package = (
            self._authority_package(session, run_id, branch_id, week, adopt=False)[0]
            if frozen is not None
            else self._package(week, required=False)
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
        current = next((s for s in slots if s.status != "complete"), None)
        executor = AuthoritativeSlotMatchExecutor(session)
        groups = session.scalars(
            select(SimulationEventGroupModel).where(
                SimulationEventGroupModel.run_id == run_id,
                SimulationEventGroupModel.branch_id == branch_id,
                SimulationEventGroupModel.week_ordinal == week.ordinal,
            )
        ).all()
        done = {g.group_id for g in groups}
        if package is None:
            body = {"scope": [run_id, branch_id, week.ordinal], "tournament": None}
            return AuthoritativeSimulationPosition(
                run_id=run_id,
                branch_id=branch_id,
                current_week=week,
                current_slot_id=None,
                slot_ordinal=None,
                unresolved_group_ids=(),
                eligible_match_ids=(),
                blocked_match_ids=(),
                current_slot_complete=True,
                supported_tournament_complete=False,
                week_ready_for_transition=False,
                transition_blockers=("supported_tournament_missing",),
                terminal_sporting_fingerprint=None,
                position_fingerprint=fingerprint(body),
            )
        matches = sorted(
            package.main_draw_matches,
            key=lambda m: (m.round_number, m.bracket_position),
        )
        sf_ids = tuple(m.match_id for m in matches[:2])
        final_id = matches[2].match_id
        if current:
            plan = executor._load_plan(current)
            unresolved = tuple(g for g in plan.group_ids if g not in done)
            eligible = tuple(
                e.match_id
                for e in plan.match_events
                if e.group_id in unresolved and set(e.feeder_group_ids or ()) <= done
            )
            blocked = tuple(
                e.match_id
                for e in plan.match_events
                if e.group_id in unresolved
                and not set(e.feeder_group_ids or ()) <= done
            )
            if current.slot_ordinal == 1:
                blocked += (final_id,)
        elif not slots:
            unresolved, eligible, blocked = sf_ids, sf_ids, (final_id,)
        elif len(slots) == 1 and slots[0].status == "complete":
            unresolved, eligible, blocked = (final_id,), (final_id,), ()
        else:
            unresolved = eligible = blocked = ()
        owned = OwnedTournamentRankingSourceStore(session).get(
            run_id=run_id, branch_id=branch_id, edition_id=package.event_id
        )
        terminal = (
            executor.terminal_checkpoint(run_id=run_id, branch_id=branch_id, week=week)
            if slots and all(s.status == "complete" for s in slots)
            else None
        )
        blockers = []
        if unresolved:
            blockers.append("pending_authoritative_groups")
        if owned is None:
            blockers.append("tournament_source_missing")
        if terminal is None:
            blockers.append("terminal_sporting_checkpoint_missing")
        lifecycle = get_lifecycle(
            session, run_id=run_id, branch_id=branch_id, week=week
        )
        if lifecycle is None:
            blockers.append("lifecycle_roster_missing")
        if not blockers:
            assert lifecycle is not None and owned is not None
            try:
                preflight_completed_context_from_authoritative_matches(
                    session,
                    run_id=run_id,
                    branch_id=branch_id,
                    completed_week=week,
                    player_ids=tuple(player.player_id for player in lifecycle.players),
                )
                if owned.binding.completed_week != week:
                    raise ValueError("owned tournament source week differs")
            except ValueError:
                blockers.append("week_transition_sporting_preflight_failed")
        blockers.extend(
            code
            for code in preview_persisted_week_transition(
                session,
                self.awards_service,
                run_id=run_id,
                branch_id=branch_id,
                completed_week=week,
            )
            if code not in blockers
        )
        ready = not blockers
        branch = session.get(RunBranchModel, branch_id)
        draft = session.scalar(
            select(BranchWorkingDraftModel).where(
                BranchWorkingDraftModel.branch_id == branch_id
            )
        )
        transition_authority = session.get(
            RankingTransitionAuthorityModel, (run_id, branch_id, week.ordinal + 1)
        )
        lifecycle_fp = lifecycle.fingerprint if lifecycle else None
        sporting = get_sporting(session, run_id=run_id, branch_id=branch_id, week=week)
        body = {
            "scope": [run_id, branch_id, week.ordinal],
            "slots": [
                (s.slot_id, s.status, s.plan_fingerprint, s.terminal_checkpoint_json)
                for s in slots
            ],
            "groups": [
                (g.group_id, g.command_fingerprint, g.result_fingerprint)
                for g in sorted(groups, key=lambda x: x.group_id)
            ],
            "owned": owned.fingerprint if owned else None,
            "tournament_authority": frozen.authority_fingerprint
            if frozen
            else self._tournament_authority_fingerprint(
                run_id,
                branch_id,
                week,
                package,
                self.awards_service.freeze_point_award_authority(package),
            ),
            "lifecycle": lifecycle_fp,
            "sporting": sporting.fingerprint if sporting else None,
            "branch_head": branch.saved_head_revision_id if branch else None,
            "draft": (
                [draft.base_revision_id, draft.status, draft.draft_version]
                if draft
                else None
            ),
            "transition_authority": (
                transition_authority.fingerprint if transition_authority else None
            ),
            "world": (
                [world.current_ordinal, world.ranking_fingerprint]
                if (
                    world := session.get(
                        AuthoritativeWorldStateModel, (run_id, branch_id)
                    )
                )
                else None
            ),
            "terminal": terminal.fingerprint if terminal else None,
        }
        return AuthoritativeSimulationPosition(
            run_id=run_id,
            branch_id=branch_id,
            current_week=week,
            current_slot_id=current.slot_id
            if current
            else (f"{package.event_id}:slot:{len(slots) + 1}" if not ready else None),
            slot_ordinal=current.slot_ordinal
            if current
            else (len(slots) + 1 if not ready else None),
            unresolved_group_ids=unresolved,
            eligible_match_ids=eligible,
            blocked_match_ids=blocked,
            current_slot_complete=not unresolved,
            supported_tournament_complete=owned is not None,
            week_ready_for_transition=ready,
            transition_blockers=tuple(blockers),
            terminal_sporting_fingerprint=terminal.fingerprint if terminal else None,
            position_fingerprint=fingerprint(body),
        )

    def _ensure_current_slot(self, session, command, package):
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
        matches = sorted(
            package.main_draw_matches,
            key=lambda m: (m.round_number, m.bracket_position),
        )
        executor = AuthoritativeSlotMatchExecutor(session)
        if pos.current_slot_id is None:
            raise ValueError("there is no current slot to materialize")
        if pos.slot_ordinal == 1:
            plans = tuple(
                SimulationMatchEventPlan(
                    group_id=m.match_id,
                    event_id=package.event_id,
                    match_id=m.match_id,
                    direct_player_ids=(m.top_player_id, m.bottom_player_id),
                )
                for m in matches[:2]
            )
            executor.create_slot(
                run_id=command.run_id,
                branch_id=command.branch_id,
                week=command.expected_week,
                slot_id=pos.current_slot_id,
                ordinal=1,
                group_ids=tuple(p.group_id for p in plans),
                match_events=plans,
                provenance=f"adopted-authority:{self._authority_package(session, command.run_id, command.branch_id, command.expected_week, adopt=False)[1]}",
            )
        elif pos.slot_ordinal == 2:
            feeders = tuple(m.match_id for m in matches[:2])
            p = SimulationMatchEventPlan(
                group_id=matches[2].match_id,
                event_id=package.event_id,
                match_id=matches[2].match_id,
                feeder_group_ids=feeders,
            )
            executor.create_slot(
                run_id=command.run_id,
                branch_id=command.branch_id,
                week=command.expected_week,
                slot_id=pos.current_slot_id,
                ordinal=2,
                group_ids=(p.group_id,),
                match_events=(p,),
                dependency_ids=feeders,
                provenance=f"adopted-authority:{self._authority_package(session, command.run_id, command.branch_id, command.expected_week, adopt=False)[1]}",
            )

    def _eligible_groups(self, session, position, package):
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

    def _execute_group(self, session, command, package, group_id):
        slot = session.get(
            SimulationSlotModel,
            (
                command.run_id,
                command.branch_id,
                command.expected_week.ordinal,
                self._position(
                    session, command.run_id, command.branch_id
                ).current_slot_id,
            ),
        )
        plan = AuthoritativeSlotMatchExecutor._load_plan(slot)
        event = next(e for e in plan.match_events if e.group_id == group_id)
        if event.direct_player_ids:
            players = event.direct_player_ids
        else:
            if event.feeder_group_ids is None:
                raise ValueError("dependent match has no feeder plan")
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

    def _advance_or_close(self, session, command, package, *, fault_at=None):
        pos = self._position(session, command.run_id, command.branch_id)
        if pos.unresolved_group_ids:
            return
        slots = session.scalars(
            select(SimulationSlotModel)
            .where(
                SimulationSlotModel.run_id == command.run_id,
                SimulationSlotModel.branch_id == command.branch_id,
                SimulationSlotModel.week_ordinal == command.expected_week.ordinal,
            )
            .order_by(SimulationSlotModel.slot_ordinal)
        ).all()
        if len(slots) == 1:
            return
        if command.expected_week.week == 61:
            raise ValueError("season_transition_required")
        executor = AuthoritativeSlotMatchExecutor(session)
        matches = sorted(
            package.main_draw_matches,
            key=lambda m: (m.round_number, m.bracket_position),
        )
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
        auth = AuthoritativeFourPlayerTournamentResult(
            event_id=package.event_id,
            semifinal_groups=(loaded[matches[0].match_id], loaded[matches[1].match_id]),
            final_group=loaded[matches[2].match_id],
            champion_player_id=loaded[matches[2].match_id].result.winner_player_id,
            match_result_fingerprints=(
                loaded[matches[0].match_id].result_fingerprint,
                loaded[matches[1].match_id].result_fingerprint,
                loaded[matches[2].match_id].result_fingerprint,
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
        if existing is not None:
            self._validate_existing_owned_source(existing, command, package, auth)
            return
        point_authority = self._point_award_authority(
            session,
            command.run_id,
            command.branch_id,
            command.expected_week,
        )
        if point_authority is None:
            raise ValueError(
                "legacy adopted tournament has no frozen point-award authority"
            )
        _, result, awards = build_authoritative_tournament_ranking_packages(
            self.awards_service,
            package=package,
            authoritative=auth,
            result_seed=self._stable_seed(package, "result"),
            award_seed=self._stable_seed(package, "awards"),
            frozen_point_authority=point_authority,
        )
        binding = TournamentRankingBinding(
            run_id=command.run_id,
            branch_id=command.branch_id,
            edition_id=package.event_id,
            event_id=package.event_id,
            completed_week=command.expected_week,
            first_publication_week=RankingWeek(
                season_index=command.expected_week.season_index,
                week=command.expected_week.week + 1,
            ),
            validity_weeks=61,
            ranking_status="ranked",
            expected_result_fingerprint=result.metadata.build_fingerprint,
            expected_award_fingerprint=awards.metadata.build_fingerprint,
        )
        prepare_tournament_ranking_sources(binding, result, awards)
        store.append(
            OwnedTournamentRankingSource(
                binding=binding,
                result=result,
                awards=awards,
                adopted_by_command_id=command.command_id,
            )
        )

    @staticmethod
    def _validate_existing_owned_source(existing, command, package, authoritative):
        binding = existing.binding
        if (
            binding.run_id != command.run_id
            or binding.branch_id != command.branch_id
            or binding.edition_id != package.event_id
            or binding.event_id != package.event_id
            or binding.completed_week != command.expected_week
        ):
            raise ValueError("Conflicting owned tournament source")
        expected = {
            group.authoritative_input.match_id: group.result_fingerprint
            for group in (
                *authoritative.semifinal_groups,
                authoritative.final_group,
            )
        }
        actual = {
            ref.match_id: ref.result_fingerprint
            for ref in existing.result.match_result_refs
        }
        if actual != expected:
            raise ValueError("Conflicting owned tournament source")
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
