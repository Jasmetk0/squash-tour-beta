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


@dataclass(frozen=True, slots=True)
class _TournamentAuthority:
    package: SeasonEventMatchPackage
    points: FrozenPointAwardAuthority
    fingerprint: str
    start_ordinal: int


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
                authorities, authority_fp = self._authority_packages(
                    session,
                    command.run_id,
                    command.branch_id,
                    before.current_week,
                    adopt=True,
                )
                self._ensure_current_slot(session, command, authorities)
                position = self._position(session, command.run_id, command.branch_id)
                targets = self._targets(session, command, mode, position, authorities)
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
                authorities = self._pending_packages(session, command, request_fp)
                current = self._position(session, command.run_id, command.branch_id)
                if group_id in current.unresolved_group_ids:
                    self._execute_group(session, command, authorities, group_id)
            if fault_at == "after_first_group" and index == 0:
                raise RuntimeError("fault after first committed group")

        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            self._require_writable_scope(session, command.run_id, command.branch_id)
            authorities = self._pending_packages(session, command, request_fp)
            self._advance_or_close(session, command, authorities, fault_at=fault_at)
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

    def _pending_packages(self, session, command, request_fp):
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
        authorities, authority_fp = self._authority_packages(
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
        return authorities

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

    def _targets(self, session, command, mode, position, authorities):
        eligible_groups = self._eligible_groups(session, position)
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

    _DAY_ORDINALS = {
        "week_start": 0,
        "mon": 0,
        "monday": 0,
        "tue": 1,
        "tuesday": 1,
        "wed": 2,
        "wednesday": 2,
        "thu": 3,
        "thursday": 3,
        "fri": 4,
        "friday": 4,
        "sat": 5,
        "saturday": 5,
        "sun": 6,
        "sunday": 6,
    }

    def _packages(self, week, *, required=True):
        season = f"{2000 + week.season_index}/{2001 + week.season_index}"
        candidates = tuple(
            sorted(
                (
                    p
                    for p in self.match_service._load_registry().matches_by_event_id.values()
                    if p.season == season and p.season_week == week.week
                ),
                key=lambda p: p.event_id,
            )
        )
        if not candidates and not required:
            return ()
        if not candidates:
            raise ValueError("supported tournament authority is missing")
        calendar = self.match_service.draw_service.calendar_service.get_calendar(
            season=season
        ).calendar
        if calendar is None:
            raise ValueError("authoritative tournament scheduling evidence is missing")
        calendar_events = {event.event_id: event for event in calendar.events}
        ordered = []
        for package in candidates:
            validate_adopted_four_player_match_package(package)
            event = calendar_events.get(package.event_id)
            if event is None or event.season_week != week.week:
                raise ValueError(
                    f"authoritative scheduling evidence is missing for {package.event_id}"
                )
            day = self._DAY_ORDINALS.get(event.start_day.strip().lower())
            if day is None:
                raise ValueError(
                    f"ambiguous authoritative scheduling evidence for {package.event_id}"
                )
            # A supported draw contributes its stored round numbers to the global
            # chronology.  Calendar start-day equality deliberately means the
            # corresponding rounds share a Simulation Slot.
            if day + max(match.round_number for match in package.main_draw_matches) > 7:
                raise ValueError(
                    f"authoritative schedule crosses the supported week for {package.event_id}"
                )
            ordered.append((day, package))
        return tuple(sorted(ordered, key=lambda item: (item[0], item[1].event_id)))

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
                    item["start_ordinal"],
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
                    0,
                ),
            )
        return ((SeasonEventMatchPackage.model_validate(payload), None, 0),)

    @staticmethod
    def _encode_adopted_authority(authorities):
        return json.dumps(
            {
                "schema_version": "adopted_tournament_authority.v3",
                "tournaments": [
                    {
                        "package": authority.package.model_dump(mode="json"),
                        "point_award_authority": authority.points.model_dump(
                            mode="json"
                        ),
                        "start_ordinal": authority.start_ordinal,
                    }
                    for authority in authorities
                ],
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    def _authority_packages(self, session, run_id, branch_id, week, *, adopt):
        row = session.get(
            AdoptedTournamentAuthorityModel, (run_id, branch_id, week.ordinal)
        )
        if row is not None:
            decoded = self._decode_adopted_authority(row.package_json)
            authorities = tuple(
                _TournamentAuthority(
                    package=package,
                    points=points,
                    start_ordinal=start,
                    fingerprint=self._tournament_authority_fingerprint(
                        run_id, branch_id, week, package, points
                    ),
                )
                for package, points, start in decoded
            )
            authority_fp = fingerprint([a.fingerprint for a in authorities])
            if authority_fp != row.authority_fingerprint and not (
                len(authorities) == 1
                and authorities[0].fingerprint == row.authority_fingerprint
            ):
                raise ValueError("frozen tournament authority is corrupt")
            # v1/v2 stored the one event fingerprint directly; retaining that
            # anchor preserves pending command/slot provenance on historical saves.
            authority_fp = row.authority_fingerprint
            return authorities, authority_fp
        if not adopt:
            raise ValueError("frozen tournament authority is missing")
        authorities = tuple(
            _TournamentAuthority(
                package=package,
                points=(
                    points := self.awards_service.freeze_point_award_authority(package)
                ),
                start_ordinal=start,
                fingerprint=self._tournament_authority_fingerprint(
                    run_id, branch_id, week, package, points
                ),
            )
            for start, package in self._packages(week)
        )
        authority_fp = fingerprint([a.fingerprint for a in authorities])
        session.add(
            AdoptedTournamentAuthorityModel(
                run_id=run_id,
                branch_id=branch_id,
                week_ordinal=week.ordinal,
                event_id="multi:"
                + fingerprint([a.package.event_id for a in authorities])[:32],
                authority_fingerprint=authority_fp,
                package_json=self._encode_adopted_authority(authorities),
            )
        )
        session.flush()
        return authorities, authority_fp

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

    @staticmethod
    def _timeline(authorities):
        timeline = {}
        for authority in authorities:
            matches = sorted(
                authority.package.main_draw_matches,
                key=lambda match: (match.round_number, match.bracket_position),
            )
            for match in matches:
                key = authority.start_ordinal + match.round_number - 1
                timeline.setdefault(key, []).append((authority, match))
        return tuple(
            (key, tuple(sorted(events, key=lambda item: item[1].match_id)))
            for key, events in sorted(timeline.items())
        )

    def _position(self, session, run_id, branch_id):
        week = self._current_week(session, run_id, branch_id)
        frozen = session.get(
            AdoptedTournamentAuthorityModel, (run_id, branch_id, week.ordinal)
        )
        if frozen is not None:
            authorities, authority_fp = self._authority_packages(
                session, run_id, branch_id, week, adopt=False
            )
        else:
            scheduled = self._packages(week, required=False)
            authorities = tuple(
                _TournamentAuthority(
                    package=package,
                    points=(
                        points := self.awards_service.freeze_point_award_authority(
                            package
                        )
                    ),
                    start_ordinal=start,
                    fingerprint=self._tournament_authority_fingerprint(
                        run_id, branch_id, week, package, points
                    ),
                )
                for start, package in scheduled
            )
            authority_fp = fingerprint([a.fingerprint for a in authorities])
        slots = session.scalars(
            select(SimulationSlotModel)
            .where(
                SimulationSlotModel.run_id == run_id,
                SimulationSlotModel.branch_id == branch_id,
                SimulationSlotModel.week_ordinal == week.ordinal,
            )
            .order_by(SimulationSlotModel.slot_ordinal)
        ).all()
        current = next((slot for slot in slots if slot.status != "complete"), None)
        executor = AuthoritativeSlotMatchExecutor(session)
        groups = session.scalars(
            select(SimulationEventGroupModel).where(
                SimulationEventGroupModel.run_id == run_id,
                SimulationEventGroupModel.branch_id == branch_id,
                SimulationEventGroupModel.week_ordinal == week.ordinal,
            )
        ).all()
        done = {group.group_id for group in groups}
        timeline = self._timeline(authorities)
        all_match_ids = tuple(
            match.match_id for _, events in timeline for _, match in events
        )
        if not authorities:
            body = {
                "scope": [run_id, branch_id, week.ordinal],
                "tournament_authorities": [],
            }
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
        if current:
            plan = executor._load_plan(current)
            unresolved = tuple(group for group in plan.group_ids if group not in done)
            eligible = tuple(
                event.match_id
                for event in plan.match_events
                if event.group_id in unresolved
                and set(event.feeder_group_ids or ()) <= done
            )
            blocked_current = tuple(
                event.match_id
                for event in plan.match_events
                if event.group_id in unresolved
                and not set(event.feeder_group_ids or ()) <= done
            )
            future = tuple(
                match_id
                for match_id in all_match_ids
                if match_id not in done and match_id not in unresolved
            )
            blocked = blocked_current + future
        else:
            next_index = len(slots)
            if next_index < len(timeline):
                events = timeline[next_index][1]
                unresolved = tuple(match.match_id for _, match in events)
                eligible = tuple(
                    match.match_id
                    for _, match in events
                    if not match.top_source.startswith("WINNER:")
                    or all(
                        feeder in done
                        for feeder in (
                            match.top_source.removeprefix("WINNER:"),
                            match.bottom_source.removeprefix("WINNER:"),
                        )
                    )
                )
                blocked = tuple(
                    match_id
                    for match_id in all_match_ids
                    if match_id not in done and match_id not in eligible
                )
            else:
                unresolved = eligible = blocked = ()
        store = OwnedTournamentRankingSourceStore(session)
        owned = {
            authority.package.event_id: store.get(
                run_id=run_id,
                branch_id=branch_id,
                edition_id=authority.package.event_id,
            )
            for authority in authorities
        }
        terminal = (
            executor.terminal_checkpoint(run_id=run_id, branch_id=branch_id, week=week)
            if slots and all(slot.status == "complete" for slot in slots)
            else None
        )
        blockers = []
        if unresolved or len(done) != len(all_match_ids):
            blockers.append("pending_authoritative_groups")
        if any(source is None for source in owned.values()):
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
                    player_ids=tuple(player.player_id for player in lifecycle.players),
                )
                if any(
                    source.binding.completed_week != week for source in owned.values()
                ):
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
        sporting = get_sporting(session, run_id=run_id, branch_id=branch_id, week=week)
        body = {
            "scope": [run_id, branch_id, week.ordinal],
            "timeline": [
                (key, [match.match_id for _, match in events])
                for key, events in timeline
            ],
            "slots": [
                (
                    slot.slot_id,
                    slot.status,
                    slot.plan_fingerprint,
                    slot.terminal_checkpoint_json,
                )
                for slot in slots
            ],
            "groups": [
                (group.group_id, group.command_fingerprint, group.result_fingerprint)
                for group in sorted(groups, key=lambda value: value.group_id)
            ],
            "owned": [
                (event_id, source.fingerprint if source else None)
                for event_id, source in sorted(owned.items())
            ],
            "tournament_authorities": [
                (a.package.event_id, a.start_ordinal, a.fingerprint)
                for a in authorities
            ],
            "authority_bundle": authority_fp,
            "lifecycle": lifecycle.fingerprint if lifecycle else None,
            "sporting": sporting.fingerprint if sporting else None,
            "branch_head": branch.saved_head_revision_id if branch else None,
            "draft": [draft.base_revision_id, draft.status, draft.draft_version]
            if draft
            else None,
            "transition_authority": transition_authority.fingerprint
            if transition_authority
            else None,
            "world": [world.current_ordinal, world.ranking_fingerprint]
            if (world := session.get(AuthoritativeWorldStateModel, (run_id, branch_id)))
            else None,
            "terminal": terminal.fingerprint if terminal else None,
        }
        next_slot = len(slots) + 1
        proposed_slot_id = (
            f"{authorities[0].package.event_id}:slot:{next_slot}"
            if len(authorities) == 1
            else f"week:{week.ordinal}:slot:{next_slot}"
        )
        return AuthoritativeSimulationPosition(
            run_id=run_id,
            branch_id=branch_id,
            current_week=week,
            current_slot_id=current.slot_id
            if current
            else (proposed_slot_id if next_slot <= len(timeline) else None),
            slot_ordinal=current.slot_ordinal
            if current
            else (next_slot if next_slot <= len(timeline) else None),
            unresolved_group_ids=unresolved,
            eligible_match_ids=eligible,
            blocked_match_ids=blocked,
            current_slot_complete=not unresolved,
            supported_tournament_complete=all(
                source is not None for source in owned.values()
            ),
            week_ready_for_transition=ready,
            transition_blockers=tuple(blockers),
            terminal_sporting_fingerprint=terminal.fingerprint if terminal else None,
            position_fingerprint=fingerprint(body),
        )

    def _ensure_current_slot(self, session, command, authorities):
        pos = self._position(session, command.run_id, command.branch_id)
        if any(
            slot.status != "complete"
            for slot in session.scalars(
                select(SimulationSlotModel).where(
                    SimulationSlotModel.run_id == command.run_id,
                    SimulationSlotModel.branch_id == command.branch_id,
                    SimulationSlotModel.week_ordinal == command.expected_week.ordinal,
                )
            ).all()
        ):
            return
        if pos.current_slot_id is None or pos.slot_ordinal is None:
            raise ValueError("there is no current slot to materialize")
        timeline = self._timeline(authorities)
        try:
            events = timeline[pos.slot_ordinal - 1][1]
        except IndexError as exc:
            raise ValueError("global tournament timeline is incoherent") from exc
        plans = []
        dependencies = []
        for authority, match in events:
            direct = None
            feeders = None
            if match.top_player_id and match.bottom_player_id:
                direct = (match.top_player_id, match.bottom_player_id)
            else:
                if not (
                    match.top_source.startswith("WINNER:")
                    and match.bottom_source.startswith("WINNER:")
                ):
                    raise ValueError("ambiguous supported match scheduling evidence")
                feeders = (
                    match.top_source.removeprefix("WINNER:"),
                    match.bottom_source.removeprefix("WINNER:"),
                )
                dependencies.extend(feeders)
            plans.append(
                SimulationMatchEventPlan(
                    group_id=match.match_id,
                    event_id=authority.package.event_id,
                    match_id=match.match_id,
                    direct_player_ids=direct,
                    feeder_group_ids=feeders,
                )
            )
        bundle_fp = self._authority_packages(
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
            ordinal=pos.slot_ordinal,
            group_ids=tuple(plan.group_id for plan in plans),
            match_events=tuple(plans),
            dependency_ids=tuple(dependencies),
            provenance=f"adopted-authority-bundle:{bundle_fp}",
        )

    def _eligible_groups(self, session, position):
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
            event.group_id
            for event in plan.match_events
            if event.match_id in position.eligible_match_ids
        )

    def _execute_group(self, session, command, authorities, group_id):
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
        event = next(item for item in plan.match_events if item.group_id == group_id)
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
                            SimulationEventGroupModel.group_id == feeder,
                        )
                    )
                ).result.winner_player_id
                for feeder in event.feeder_group_ids
            )
        authority = next(
            value for value in authorities if value.package.event_id == event.event_id
        )
        seed = int(
            hashlib.sha256(
                f"{command.run_id}|{command.branch_id}|{command.expected_week.ordinal}|{authority.fingerprint}|{group_id}".encode()
            ).hexdigest()[:15],
            16,
        )
        AuthoritativeSlotMatchExecutor(session).execute_match_group(
            run_id=command.run_id,
            branch_id=command.branch_id,
            week=command.expected_week,
            slot_id=slot.slot_id,
            group_id=group_id,
            event_id=event.event_id,
            match_id=event.match_id,
            player_a_id=players[0],
            player_b_id=players[1],
            seed=seed,
            expected_slot_start_fingerprint=plan.slot_start_fingerprint,
        )

    def _advance_or_close(self, session, command, authorities, *, fault_at=None):
        if command.expected_week.week == 61:
            raise ValueError("season_transition_required")
        executor = AuthoritativeSlotMatchExecutor(session)
        loaded = {
            group.group_id: executor._load_group(group)
            for group in session.scalars(
                select(SimulationEventGroupModel).where(
                    SimulationEventGroupModel.run_id == command.run_id,
                    SimulationEventGroupModel.branch_id == command.branch_id,
                    SimulationEventGroupModel.week_ordinal
                    == command.expected_week.ordinal,
                )
            ).all()
        }
        store = OwnedTournamentRankingSourceStore(session)
        for authority in authorities:
            package = authority.package
            matches = sorted(
                package.main_draw_matches,
                key=lambda match: (match.round_number, match.bracket_position),
            )
            if not all(match.match_id in loaded for match in matches):
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
                    loaded[match.match_id].result_fingerprint for match in matches
                ),
            )
            if fault_at == "after_final_before_source":
                raise RuntimeError(
                    "fault after tournament final before ranking source persistence"
                )
            existing = store.get(
                run_id=command.run_id,
                branch_id=command.branch_id,
                edition_id=package.event_id,
            )
            if existing is not None:
                self._validate_existing_owned_source(existing, command, package, auth)
                continue
            if authority.points is None:
                raise ValueError(
                    "legacy adopted tournament has no frozen point-award authority"
                )
            _, result, awards = build_authoritative_tournament_ranking_packages(
                self.awards_service,
                package=package,
                authoritative=auth,
                result_seed=self._stable_seed(package, "result"),
                award_seed=self._stable_seed(package, "awards"),
                frozen_point_authority=authority.points,
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
