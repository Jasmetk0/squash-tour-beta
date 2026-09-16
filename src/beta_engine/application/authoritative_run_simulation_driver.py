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
from beta_engine.domain.simulation_slots import (
    SimulationMatchEventPlan,
    WeekSimulationSchedule,
    fingerprint,
)
from beta_engine.infrastructure.db.models import (
    AuthoritativeSimulationCommandModel,
    AuthoritativeWorldStateModel,
    AdoptedTournamentAuthorityModel,
    BranchWorkingDraftModel,
    PlayerSportingWeekStateModel,
    RunBranchModel,
    RunContainerModel,
    SimulationEventGroupModel,
    SimulationSlotModel,
    WeekSimulationScheduleModel,
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

    def _packages(self, week, *, required=True):
        season = f"{2000 + week.season_index}/{2001 + week.season_index}"
        packages = tuple(
            p
            for p in self.match_service._load_registry().matches_by_event_id.values()
            if p.season == season and p.season_week == week.week
        )
        if not packages and required:
            raise ValueError("supported tournament authority is missing")
        for package in packages:
            validate_adopted_four_player_match_package(package)
        return packages

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
        if payload.get("schema_version") == "adopted_tournament_authority.v3":
            return tuple(
                (
                    SeasonEventMatchPackage.model_validate(item["package"]),
                    FrozenPointAwardAuthority.model_validate(
                        item["point_award_authority"]
                    ),
                )
                for item in payload["tournaments"]
            )
        if payload.get("schema_version") == "adopted_tournament_authority.v2":
            return (
                (
                    SeasonEventMatchPackage.model_validate(payload["package"]),
                    FrozenPointAwardAuthority.model_validate(
                        payload["point_award_authority"]
                    ),
                ),
            )
        return ((SeasonEventMatchPackage.model_validate(payload), None),)

    @staticmethod
    def _encode_adopted_authority(items):
        return json.dumps(
            {
                "schema_version": "adopted_tournament_authority.v3",
                "tournaments": [
                    {
                        "package": p.model_dump(mode="json"),
                        "point_award_authority": a.model_dump(mode="json"),
                    }
                    for p, a in items
                ],
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    def _authority_package(self, session, run_id, branch_id, week, *, adopt):
        row = session.get(
            AdoptedTournamentAuthorityModel, (run_id, branch_id, week.ordinal)
        )
        if row is not None:
            items = self._decode_adopted_authority(row.package_json)
            packages = tuple(p for p, _ in items)
            authority_fp = self._tournament_authority_fingerprint(
                run_id, branch_id, week, items
            )
            if authority_fp != row.authority_fingerprint:
                raise ValueError("frozen tournament authority is corrupt")
            return packages, authority_fp
        if not adopt:
            raise ValueError("frozen tournament authority is missing")
        packages = self._packages(week)
        if (
            len(packages) > 1
            and self._schedule(session, run_id, branch_id, week) is None
        ):
            raise ValueError(
                "multiple supported tournaments lack authoritative cross-event Simulation Slot chronology"
            )
        items = tuple(
            (p, self.awards_service.freeze_point_award_authority(p)) for p in packages
        )
        authority_fp = self._tournament_authority_fingerprint(
            run_id, branch_id, week, items
        )
        session.add(
            AdoptedTournamentAuthorityModel(
                run_id=run_id,
                branch_id=branch_id,
                week_ordinal=week.ordinal,
                event_id=packages[0].event_id,
                authority_fingerprint=authority_fp,
                package_json=self._encode_adopted_authority(items),
            )
        )
        session.flush()
        return packages, authority_fp

    @staticmethod
    def _tournament_authority_fingerprint(run_id, branch_id, week, items):
        bodies = []
        for package, point_authority in items:
            payload = package.model_dump(mode="json")
            payload["metadata"].pop("persistence_path", None)
            bodies.append(
                {
                    "package": payload,
                    "point_award_authority": point_authority.model_dump(mode="json")
                    if point_authority
                    else None,
                }
            )
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
            packages = self._packages(week, required=False)
            schedule = self._schedule(session, run_id, branch_id, week)
            requirement_position = self._position(
                session, run_id, branch_id, allow_missing_schedule=True
            )
            return {
                "run_id": run_id,
                "branch_id": branch_id,
                "week": week.model_dump(mode="json"),
                "required": len(packages) > 1,
                "event_ids": [p.event_id for p in packages],
                "group_ids": [
                    m.match_id for p in packages for m in p.main_draw_matches
                ],
                "schedule": schedule.model_dump(mode="json") if schedule else None,
                "schedule_fingerprint": schedule.fingerprint if schedule else None,
                "expected_position_fingerprint": requirement_position.position_fingerprint,
            }

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
            packages = self._packages(schedule.week)
            self._validate_schedule(schedule, packages)
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
            self._validate_schedule(schedule, self._packages(schedule.week))
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
        plans = {}
        for package in packages:
            matches = sorted(
                package.main_draw_matches,
                key=lambda m: (m.round_number, m.bracket_position),
            )
            feeders = tuple(m.match_id for m in matches[:2])
            for match in matches[:2]:
                plans[match.match_id] = SimulationMatchEventPlan(
                    group_id=match.match_id,
                    event_id=package.event_id,
                    match_id=match.match_id,
                    direct_player_ids=(match.top_player_id, match.bottom_player_id),
                )
            plans[matches[2].match_id] = SimulationMatchEventPlan(
                group_id=matches[2].match_id,
                event_id=package.event_id,
                match_id=matches[2].match_id,
                feeder_group_ids=feeders,
            )
        return plans

    def _validate_schedule(self, schedule, packages):
        plans = self._topology(packages)
        authored = {g for slot in schedule.slots for g in slot.group_ids}
        if authored != set(plans):
            raise ValueError("schedule must cover every supported group exactly once")
        ordinal = {g: slot.ordinal for slot in schedule.slots for g in slot.group_ids}
        for group_id, plan in plans.items():
            for feeder in plan.feeder_group_ids or ():
                if ordinal[feeder] >= ordinal[group_id]:
                    raise ValueError(
                        "dependent groups require a strictly later slot than feeders"
                    )

    def _position(self, session, run_id, branch_id, *, allow_missing_schedule=False):
        week = self._current_week(session, run_id, branch_id)
        frozen = session.get(
            AdoptedTournamentAuthorityModel, (run_id, branch_id, week.ordinal)
        )
        packages = (
            self._authority_package(session, run_id, branch_id, week, adopt=False)[0]
            if frozen
            else self._packages(week, required=False)
        )
        schedule = self._schedule(session, run_id, branch_id, week)
        if len(packages) > 1 and schedule is None and not allow_missing_schedule:
            raise ValueError(
                "multiple supported tournaments lack authoritative cross-event Simulation Slot chronology"
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
        plans = self._topology(packages) if packages else {}
        current = next((s for s in slots if s.status != "complete"), None)
        authored_slots = schedule.slots if schedule else ()
        if not authored_slots and len(packages) == 1:
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
            g for g in unresolved if set(plans[g].feeder_group_ids or ()) <= done
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
        if len(packages) > 1 and schedule is None:
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
                        (p, self.awards_service.freeze_point_award_authority(p))
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
                f"week-{week.ordinal}:slot:{next_spec.ordinal}" if next_spec else None
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
        plans = self._topology(packages)
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
            dependency_ids=tuple(
                f for p in selected for f in (p.feeder_group_ids or ())
            ),
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
        if event.direct_player_ids:
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
        if command.expected_week.week == 61:
            raise ValueError("season_transition_required")
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
        for package, point_authority in items:
            matches = sorted(
                package.main_draw_matches,
                key=lambda m: (m.round_number, m.bracket_position),
            )
            if not all(m.match_id in loaded for m in matches):
                continue
            auth = AuthoritativeFourPlayerTournamentResult(
                event_id=package.event_id,
                semifinal_groups=(
                    loaded[matches[0].match_id],
                    loaded[matches[1].match_id],
                ),
                final_group=loaded[matches[2].match_id],
                champion_player_id=loaded[matches[2].match_id].result.winner_player_id,
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
            for g in (*authoritative.semifinal_groups, authoritative.final_group)
        }
        if {
            r.match_id: r.result_fingerprint for r in existing.result.match_result_refs
        } != expected:
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
